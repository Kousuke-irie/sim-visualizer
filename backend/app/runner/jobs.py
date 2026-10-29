"""計算の待ち行列（DESIGN_research_features.md §4.3〜§4.5）。

- 実行するのは1本ずつ。順番が来たら gfortran でコンパイルし、新しいランの中で `caffeinate -i ./a.out` を実行する
- 実行できるのは、このアプリで作った（simviz_run.json があり、まだ実行していない）ランだけ。
  結果を上書きしないよう、実行は1回限り
- コマンドはシェルを介さず引数の配列で起動する。コンパイルコマンドは作成時と同じ検査（parse_compile_command）を通す
- 待ち行列はファイル（既定 ~/.simviz/jobs.json）に保存する。計算は runner とは別のプロセスグループで動かすので、
  7時間の計算中に runner を再起動しても計算は止まらない。再起動後は、生きている計算を見張り直し、
  プロセスが無くなっていたものは「中断」にする
"""

import datetime as dt
import json
import os
import shutil
import signal
import subprocess
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from app.errors import AccessDeniedError, ConflictError, InvalidInputError, NotFoundError
from app.models.jobs import Job, JobLog, JobStatus
from app.runner.compile_command import parse_compile_command
from app.runner.runs import LOG_FILE, RECORD_FILE, _parse_base_input
from app.services.path_policy import PathNotAllowedError, resolve_within_data_roots

JOBS_FILE_ENV = "SIMVIZ_JOBS_FILE"
DEFAULT_JOBS_FILE = Path.home() / ".simviz" / "jobs.json"

ACTIVE: set[str] = {"queued", "compiling", "running"}
LOG_TAIL_BYTES = 256 * 1024  # ログが数百MBになっても末尾だけを読む


@dataclass
class _JobState:
    """jobs.json に保存する1件分。API の Job は、ここに進捗（ファイル数・経過時間）を足して作る。"""

    job_id: str
    name: str
    run_dir: str
    base_run: str
    compile_argv: list[str]
    executable: str
    field_dir: str
    frames_expected: int
    created_at: float
    status: JobStatus = "queued"
    message: str = ""
    started_at: float | None = None
    run_started_at: float | None = None  # a.out を起動した時刻（終了予定はここから求める）
    finished_at: float | None = None
    exit_code: int | None = None
    pid: int | None = None  # 実行中のプロセスグループの先頭（再起動後に見張り直すために保存する）
    cancel_requested: bool = False


def _iso(t: float | None) -> str | None:
    return dt.datetime.fromtimestamp(t, dt.UTC).isoformat() if t is not None else None


def estimate_eta(frames_done: int, frames_expected: int, elapsed: float) -> float | None:
    """1フレームあたりの平均時間から、終了までの残り時間を見込む。

    最初の1枚（t=0）は計算を始めてすぐ書き出されるので、間隔は frames_done - 1 個で割る。
    2枚目が出るまでは見込みが立たないので None。
    """
    if frames_done < 2 or frames_expected <= frames_done:
        return None if frames_done < 2 else 0.0
    return elapsed / (frames_done - 1) * (frames_expected - frames_done)


def _count_frames(field_dir: str) -> int:
    try:
        return sum(1 for p in Path(field_dir).glob("tec-*.plt"))
    except OSError:
        return 0


def _process_alive(pid: int, *, reap: bool = False) -> bool:
    """pid が、このアプリが起動したプロセスグループの先頭として生きているか。

    pid が別のプロセスに再利用されていても騙されないよう、pgid も確かめる。
    reap=True では、終わって回収待ち（ゾンビ）になっている自分の子を回収してから判定する。
    Linux ではゾンビにも kill(pid, 0) が成功するため、回収しないと「生きている」と見え続ける。
    Popen で待っている子に使うと終了コードを横取りしてしまうので、見張り直している計算にだけ使う。
    """
    if reap:
        try:
            if os.waitpid(pid, os.WNOHANG)[0] == pid:
                return False
        except ChildProcessError:
            pass  # 自分の子ではない（runner の再起動前に起動した計算）
    try:
        os.kill(pid, 0)
        return os.getpgid(pid) == pid
    except (ProcessLookupError, PermissionError):
        return False


def _update_record(run_dir: str, **fields) -> None:
    path = Path(run_dir) / RECORD_FILE
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    record.update(fields)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


class JobQueue:
    def __init__(
        self,
        state_file: Path,
        *,
        term_grace: float = 10.0,
        poll_interval: float = 1.0,
        clock: Callable[[], float] = time.time,
    ):
        self._state_file = state_file
        self._term_grace = term_grace  # SIGTERM のあと SIGKILL するまでの猶予[秒]
        self._poll = poll_interval
        self._clock = clock
        self._cond = threading.Condition()
        self._jobs: list[_JobState] = []
        self._stopping = False
        self._thread: threading.Thread | None = None
        self._load_and_recover()

    # ---- 保存と復旧 ----

    def _load_and_recover(self) -> None:
        if not self._state_file.is_file():
            return
        raw = json.loads(self._state_file.read_text(encoding="utf-8"))
        self._jobs = [_JobState(**j) for j in raw.get("jobs", [])]
        for job in self._jobs:
            if job.status == "compiling":
                # コンパイルは数十秒で終わる。続きの実行を引き継げないので、残っていれば止めて中断にする
                if job.pid and _process_alive(job.pid):
                    os.killpg(job.pid, signal.SIGKILL)
                self._finish(job, "interrupted", "runner の再起動でコンパイルが中断されました", save=False)
            elif job.status == "running" and not (job.pid and _process_alive(job.pid)):
                self._finish_unwatched(job, save=False)
        self._save()

    def _save(self) -> None:
        self._state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._state_file.with_suffix(".tmp")
        tmp.write_text(json.dumps({"jobs": [asdict(j) for j in self._jobs]}, ensure_ascii=False, indent=2))
        os.replace(tmp, self._state_file)  # 書きかけの jobs.json を残さない

    # ---- 受付 ----

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._worker, name="simviz-jobs", daemon=True)
            self._thread.start()

    def shutdown(self) -> None:
        """待ち行列の処理を止める（テスト用）。実行中の計算は止めない。"""
        with self._cond:
            self._stopping = True
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def submit(self, run_dir: str) -> Job:
        try:
            run = Path(resolve_within_data_roots(run_dir))
        except PathNotAllowedError:
            raise AccessDeniedError("許可されたデータディレクトリの外にはアクセスできません") from None
        if not run.is_dir():
            raise NotFoundError("ランが見つかりません")
        record_path = run / RECORD_FILE
        if not record_path.is_file():
            raise InvalidInputError(f"このアプリで作ったランだけ実行できます（{RECORD_FILE} がありません）")
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if record.get("status") != "created":
            raise ConflictError("このランは既に実行しました（結果を上書きしないよう、実行は1回だけです）")

        argv = parse_compile_command(record.get("compile_command", ""), run)
        executable = argv[argv.index("-o") + 1] if "-o" in argv else "a.out"
        input_text = (run / "input.dat").read_text(encoding="utf-8", errors="replace")
        parsed = _parse_base_input(run, input_text)
        job = _JobState(
            job_id=uuid.uuid4().hex[:12],
            name=run.name,
            run_dir=str(run),
            base_run=str(record.get("base_run", "")),
            compile_argv=argv,
            executable=executable,
            field_dir=str(run / parsed.result_dirs["field2"]),
            frames_expected=round(parsed.endtime / parsed.ifit2) + 1,
            created_at=self._clock(),
        )
        with self._cond:
            if any(j.run_dir == job.run_dir and j.status in ACTIVE for j in self._jobs):
                raise ConflictError("このランは既に待ち行列にあります")
            self._jobs.append(job)
            _update_record(job.run_dir, status="queued")
            self._save()
            self._cond.notify_all()
            return self._to_api(job)  # 処理が始まる前の状態（queued）を返す

    def jobs(self) -> list[Job]:
        with self._cond:
            return [self._to_api(j) for j in reversed(self._jobs)]  # 新しいものから

    def get(self, job_id: str) -> Job:
        with self._cond:
            return self._to_api(self._find(job_id))

    def cancel(self, job_id: str) -> Job:
        with self._cond:
            job = self._find(job_id)
            if job.status not in ACTIVE:
                raise ConflictError("終わった計算は中止できません")
            if job.status == "queued":
                self._finish(job, "cancelled", "実行前に中止しました")
                return self._to_api(job)
            job.cancel_requested = True
            pid = job.pid
            self._save()
        if pid:
            self._terminate(pid)
        return self.get(job_id)

    def log_tail(self, job_id: str, lines: int) -> JobLog:
        with self._cond:
            job = self._find(job_id)
        path = Path(job.run_dir) / LOG_FILE
        if not path.is_file():
            return JobLog(job_id=job_id, text="", truncated=False)
        with path.open("rb") as f:
            size = f.seek(0, os.SEEK_END)
            f.seek(max(0, size - LOG_TAIL_BYTES))
            text = f.read().decode("utf-8", errors="replace")
        all_lines = text.splitlines()
        tail = all_lines[-lines:]
        return JobLog(job_id=job_id, text="\n".join(tail), truncated=size > LOG_TAIL_BYTES or len(all_lines) > lines)

    # ---- 内部 ----

    def _find(self, job_id: str) -> _JobState:
        for job in self._jobs:
            if job.job_id == job_id:
                return job
        raise NotFoundError("指定された計算が見つかりません")

    def _to_api(self, job: _JobState) -> Job:
        frames = _count_frames(job.field_dir)
        elapsed = eta = None
        if job.status == "running" and job.run_started_at is not None:
            elapsed = self._clock() - job.run_started_at
            eta = estimate_eta(frames, job.frames_expected, elapsed)
        elif job.started_at is not None:
            elapsed = (job.finished_at or self._clock()) - job.started_at
        return Job(
            job_id=job.job_id,
            name=job.name,
            run_dir=job.run_dir,
            base_run=job.base_run,
            status=job.status,
            message=job.message,
            created_at=_iso(job.created_at),
            started_at=_iso(job.started_at),
            finished_at=_iso(job.finished_at),
            exit_code=job.exit_code,
            frames_done=frames,
            frames_expected=job.frames_expected,
            elapsed_sec=elapsed,
            eta_sec=eta,
        )

    def _finish(self, job: _JobState, status: JobStatus, message: str, *, exit_code=None, save=True) -> None:
        job.status = status
        job.message = message
        job.exit_code = exit_code
        job.finished_at = self._clock()
        job.pid = None
        _update_record(
            job.run_dir,
            status=status,
            started_at=_iso(job.started_at),
            finished_at=_iso(job.finished_at),
            exit_code=exit_code,
        )
        if save:
            self._save()
            self._cond.notify_all()

    def _finish_unwatched(self, job: _JobState, save=True) -> None:
        """runner が見ていない間に終わった計算。終了コードは分からないので、出力が揃ったかで判断する。"""
        if _count_frames(job.field_dir) >= job.frames_expected:
            self._finish(
                job, "succeeded", "出力はすべて揃っています（runner の停止中に終わったため終了コードは不明）", save=save
            )
        else:
            self._finish(job, "interrupted", "runner の停止中に計算が止まりました（出力が途中までです）", save=save)

    def _terminate(self, pid: int) -> None:
        """プロセスグループに SIGTERM、猶予のあいだに終わらなければ SIGKILL。"""
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            return

        def kill_later():
            deadline = time.monotonic() + self._term_grace
            while time.monotonic() < deadline:
                if not _process_alive(pid):
                    return
                time.sleep(0.1)
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass

        threading.Thread(target=kill_later, daemon=True).start()

    def _next(self) -> _JobState | None:
        # runner の再起動前から動いている計算があれば、それが終わるまで次を始めない（同時に1本）
        for job in self._jobs:
            if job.status == "running":
                return job
        return next((j for j in self._jobs if j.status == "queued"), None)

    def _worker(self) -> None:
        while True:
            with self._cond:
                while not self._stopping and self._next() is None:
                    self._cond.wait(timeout=self._poll)
                if self._stopping:
                    return
                job = self._next()
            if job.status == "queued":
                self._execute(job)
            else:
                self._watch_unowned(job)

    def _watch_unowned(self, job: _JobState) -> None:
        while job.pid and _process_alive(job.pid, reap=True):
            with self._cond:
                if self._stopping:
                    return
                self._cond.wait(timeout=self._poll)
        with self._cond:
            if job.cancel_requested:
                self._finish(job, "cancelled", "中止しました")
            else:
                self._finish_unwatched(job)

    def _spawn(self, job: _JobState, argv: list[str], log) -> subprocess.Popen:
        # 別のセッション（プロセスグループ）で起動する。中止はグループごと止め、runner の終了（Ctrl-C）は伝えない
        proc = subprocess.Popen(argv, cwd=job.run_dir, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        with self._cond:
            job.pid = proc.pid
            self._save()
            cancelled = job.cancel_requested
        if cancelled:  # 起動の直前に中止された
            self._terminate(proc.pid)
        return proc

    def _execute(self, job: _JobState) -> None:
        with self._cond:
            job.status = "compiling"
            job.started_at = self._clock()
            self._save()
            self._cond.notify_all()
        gfortran_version = self._gfortran_version(job.compile_argv[0])
        _update_record(job.run_dir, status="compiling", gfortran_version=gfortran_version)

        with (Path(job.run_dir) / LOG_FILE).open("ab") as log:
            try:
                log.write(f"$ {' '.join(job.compile_argv)}\n".encode())
                log.flush()
                rc = self._spawn(job, job.compile_argv, log).wait()
                with self._cond:
                    if job.cancel_requested:
                        return self._finish(job, "cancelled", "コンパイル中に中止しました", exit_code=rc)
                    if rc != 0:
                        return self._finish(job, "failed", f"コンパイルに失敗しました（終了コード {rc}）", exit_code=rc)

                exe = f"./{job.executable}"
                # caffeinate -i で、計算中に Mac がスリープしないようにする（無い環境ではそのまま実行）
                argv = ["caffeinate", "-i", exe] if shutil.which("caffeinate") else [exe]
                log.write(f"$ {' '.join(argv)}\n".encode())
                log.flush()
                with self._cond:
                    job.status = "running"
                    job.run_started_at = self._clock()
                    self._cond.notify_all()
                _update_record(job.run_dir, status="running")
                rc = self._spawn(job, argv, log).wait()
            except OSError as e:
                with self._cond:
                    return self._finish(job, "failed", f"起動できませんでした: {e}")
        with self._cond:
            if job.cancel_requested:
                self._finish(job, "cancelled", "計算を中止しました", exit_code=rc)
            elif rc == 0:
                self._finish(job, "succeeded", "", exit_code=rc)
            else:
                self._finish(job, "failed", f"計算が終了コード {rc} で終わりました", exit_code=rc)

    @staticmethod
    def _gfortran_version(compiler: str) -> str | None:
        try:
            out = subprocess.run([compiler, "--version"], capture_output=True, text=True, timeout=30).stdout
        except (OSError, subprocess.TimeoutExpired):
            return None
        return out.splitlines()[0] if out else None


_queue: JobQueue | None = None
_queue_lock = threading.Lock()


def get_queue() -> JobQueue:
    """runner プロセスで1つの待ち行列。最初に呼ばれたときに保存ファイルから復旧し、処理を始める。"""
    global _queue
    with _queue_lock:
        if _queue is None:
            _queue = JobQueue(Path(os.environ.get(JOBS_FILE_ENV) or DEFAULT_JOBS_FILE))
            _queue.start()
        return _queue

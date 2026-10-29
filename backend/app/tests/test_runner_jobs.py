"""計算の待ち行列（runner, DESIGN_research_features.md §4.3〜§4.5）。

本物の gfortran とモデルの代わりに、偽の gfortran（sample_data.write_fake_toolchain）を PATH の先頭に置く。
偽の gfortran が作る a.out は、input.dat の endtime / ifit2 枚の tec-*.plt を少しずつ書き出す（本物と同じ枚数）。
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from app.errors import AccessDeniedError, ConflictError, InvalidInputError
from app.models.runs import NewRunSpec
from app.runner.jobs import JobQueue, estimate_eta
from app.runner.runs import LOG_FILE, RECORD_FILE, create_run
from app.tests.sample_data import write_fake_toolchain, write_simulation_dir

COMPILE = "gfortran -O2 -o a.out mecnest.f90"


@pytest.fixture(autouse=True)
def fake_toolchain(data_root, monkeypatch):
    bin_dir = write_fake_toolchain(data_root / "bin")
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("FAKE_MODEL_FRAME_SECONDS", "0.05")
    return bin_dir


@pytest.fixture
def base(data_root):
    return write_simulation_dir(data_root / "runs" / "case_v1", with_source=True)


def new_run(base, name="case_v2"):
    return create_run(str(base), NewRunSpec(name=name, compile_command=COMPILE)).path


@pytest.fixture
def queue(tmp_path):
    q = JobQueue(tmp_path / "state" / "jobs.json", term_grace=1.0, poll_interval=0.05)
    q.start()
    yield q
    q.shutdown()


def wait_for(queue, job_id, statuses, timeout=15.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = queue.get(job_id)
        if job.status in statuses:
            return job
        time.sleep(0.02)
    raise AssertionError(f"{statuses} になりませんでした（現在: {queue.get(job_id).status}）")


def record(run_dir):
    return json.loads((Path(run_dir) / RECORD_FILE).read_text())


def test_job_compiles_runs_and_records_the_result(queue, base):
    run = new_run(base)
    job = queue.submit(run)
    # 実際のモデルは tec-00000 〜 tec-(endtime/ifit2 - 1) を書く（v16: endtime 86400 で24枚）。ここでは 7200 / 3600 = 2
    assert job.status == "queued" and job.frames_expected == 2

    done = wait_for(queue, job.job_id, {"succeeded", "failed"})
    assert done.status == "succeeded", done.message
    assert done.exit_code == 0 and done.frames_done == done.frames_expected == 2
    assert sorted(p.name for p in (base.parent / "case_v2" / "field2").iterdir()) == ["tec-00000.plt", "tec-00001.plt"]
    log = (base.parent / "case_v2" / LOG_FILE).read_text()
    assert "$ gfortran -O2 -o a.out mecnest.f90" in log and "fake model: done" in log

    rec = record(run)
    assert rec["status"] == "succeeded" and rec["exit_code"] == 0
    assert rec["gfortran_version"] == "GNU Fortran (fake) 0.0"
    assert rec["started_at"] and rec["finished_at"]


def test_only_one_job_runs_at_a_time(queue, base, monkeypatch):
    monkeypatch.setenv("FAKE_MODEL_FRAME_SECONDS", "0.3")
    first = queue.submit(new_run(base, "case_v2"))
    second = queue.submit(new_run(base, "case_v3"))
    wait_for(queue, first.job_id, {"running"})
    assert queue.get(second.job_id).status == "queued"
    wait_for(queue, first.job_id, {"succeeded"})
    assert wait_for(queue, second.job_id, {"succeeded"}).frames_done == 2
    assert [j.name for j in queue.jobs()] == ["case_v3", "case_v2"]  # 新しいものから


def test_compile_error_fails_the_job_without_running(queue, base, monkeypatch):
    monkeypatch.setenv("FAKE_GFORTRAN_FAIL", "1")
    job = queue.submit(new_run(base))
    done = wait_for(queue, job.job_id, {"succeeded", "failed"})
    assert done.status == "failed" and "コンパイル" in done.message and done.exit_code == 1
    assert done.frames_done == 0
    assert "fake compile error" in queue.log_tail(job.job_id, 50).text


def test_nonzero_exit_of_the_model_is_a_failure(queue, base, monkeypatch):
    monkeypatch.setenv("FAKE_MODEL_EXIT", "3")
    job = queue.submit(new_run(base))
    done = wait_for(queue, job.job_id, {"succeeded", "failed"})
    assert done.status == "failed" and done.exit_code == 3 and "3" in done.message


def test_running_job_can_be_cancelled(queue, base, monkeypatch):
    monkeypatch.setenv("FAKE_MODEL_FRAME_SECONDS", "5")
    job = queue.submit(new_run(base))
    wait_for(queue, job.job_id, {"running"})
    started = time.monotonic()
    queue.cancel(job.job_id)
    done = wait_for(queue, job.job_id, {"cancelled", "failed", "succeeded"})
    assert done.status == "cancelled"
    assert time.monotonic() - started < 3  # 5秒の待ちを最後まで待たない
    assert record(done.run_dir)["status"] == "cancelled"
    with pytest.raises(ConflictError):
        queue.cancel(job.job_id)


def test_queued_job_can_be_cancelled_before_it_starts(queue, base, monkeypatch):
    monkeypatch.setenv("FAKE_MODEL_FRAME_SECONDS", "0.3")
    first = queue.submit(new_run(base, "case_v2"))
    second = queue.submit(new_run(base, "case_v3"))
    assert queue.cancel(second.job_id).status == "cancelled"
    wait_for(queue, first.job_id, {"succeeded"})
    assert queue.get(second.job_id).status == "cancelled"
    assert not (base.parent / "case_v3" / LOG_FILE).exists()  # 一度も起動していない


def test_a_run_can_only_be_executed_once(queue, base):
    run = new_run(base)
    job = queue.submit(run)
    with pytest.raises(ConflictError):
        queue.submit(run)  # 待ち行列にある
    wait_for(queue, job.job_id, {"succeeded"})
    with pytest.raises(ConflictError):
        queue.submit(run)  # 実行済み（結果を上書きしない）


def test_only_runs_created_by_the_app_can_be_executed(queue, base, data_root):
    # 元のラン（手作業のラン）には simviz_run.json が無い
    with pytest.raises(InvalidInputError, match=RECORD_FILE):
        queue.submit(str(base))


def test_runs_outside_the_data_roots_are_rejected(queue, tmp_path_factory):
    outside = write_simulation_dir(tmp_path_factory.mktemp("outside") / "run")
    with pytest.raises(AccessDeniedError):
        queue.submit(str(outside))


def test_compile_command_in_the_record_is_checked_again(queue, base):
    # simviz_run.json は作成後に書き換えられうるので、実行時にも検査する
    run = new_run(base)
    path = base.parent / "case_v2" / RECORD_FILE
    rec = json.loads(path.read_text())
    rec["compile_command"] = "sh -c 'rm -rf ~'"
    path.write_text(json.dumps(rec))
    with pytest.raises(InvalidInputError):
        queue.submit(run)


def test_log_tail_returns_the_last_lines(queue, base):
    job = queue.submit(new_run(base))
    wait_for(queue, job.job_id, {"succeeded"})
    tail = queue.log_tail(job.job_id, 2)
    assert tail.text.splitlines() == ["time = 3600.0 s", "fake model: done"]
    assert tail.truncated


def test_state_survives_a_restart(tmp_path, base):
    state = tmp_path / "state" / "jobs.json"
    q = JobQueue(state, poll_interval=0.05)
    q.start()
    job = q.submit(new_run(base))
    wait_for(q, job.job_id, {"succeeded"})
    q.shutdown()

    restarted = JobQueue(state)
    assert restarted.get(job.job_id).status == "succeeded"


def write_state(state, run_dir, status, pid, frames_expected=3):
    state.parent.mkdir(parents=True, exist_ok=True)
    job = {
        "job_id": "j1",
        "name": "case_v2",
        "run_dir": str(run_dir),
        "base_run": "",
        "compile_argv": ["gfortran", "-o", "a.out", "mecnest.f90"],
        "executable": "a.out",
        "field_dir": str(run_dir / "field2"),
        "frames_expected": frames_expected,
        "created_at": time.time(),
        "status": status,
        "started_at": time.time(),
        "run_started_at": time.time(),
        "pid": pid,
    }
    state.write_text(json.dumps({"jobs": [job]}))


def dead_pid():
    proc = subprocess.Popen([sys.executable, "-c", "pass"], start_new_session=True)
    proc.wait()
    return proc.pid


def test_running_job_whose_process_is_gone_becomes_interrupted(tmp_path, base):
    run = base.parent / "case_v2"
    new_run(base)
    state = tmp_path / "jobs.json"
    write_state(state, run, "running", dead_pid())
    q = JobQueue(state)
    job = q.get("j1")
    assert job.status == "interrupted" and "停止中" in job.message
    assert record(run)["status"] == "interrupted"


def test_running_job_that_finished_while_runner_was_down_counts_as_succeeded(tmp_path, base):
    run = base.parent / "case_v2"
    new_run(base)
    for t in range(2):
        (run / "field2" / f"tec-{t:05d}.plt").write_text("")
    state = tmp_path / "jobs.json"
    write_state(state, run, "running", dead_pid(), frames_expected=2)
    job = JobQueue(state).get("j1")
    assert job.status == "succeeded" and job.exit_code is None and "不明" in job.message


def test_job_still_running_after_restart_is_watched_and_blocks_the_queue(tmp_path, base):
    run = base.parent / "case_v2"
    new_run(base)
    # runner の再起動前から動き続けている計算（runner とは別のプロセスグループ）
    proc = subprocess.Popen(["sleep", "30"], start_new_session=True)
    try:
        state = tmp_path / "jobs.json"
        write_state(state, run, "running", proc.pid)
        q = JobQueue(state, term_grace=1.0, poll_interval=0.05)
        q.start()
        try:
            assert q.get("j1").status == "running"
            other = q.submit(new_run(base, "case_v3"))
            time.sleep(0.3)
            assert q.get(other.job_id).status == "queued"  # 同時に1本

            q.cancel("j1")  # 自分の子でないプロセスも、プロセスグループごと止められる
            assert wait_for(q, "j1", {"cancelled"}).status == "cancelled"
            assert wait_for(q, other.job_id, {"succeeded"}).status == "succeeded"
        finally:
            q.shutdown()
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()


@pytest.mark.parametrize(
    ("done", "expected", "elapsed", "eta"),
    [
        (0, 10, 5.0, None),
        (1, 10, 5.0, None),  # 2枚目が出るまでは見込みが立たない
        (2, 10, 60.0, 480.0),  # 1間隔 60 秒、残り 8 枚
        (11, 11, 600.0, 0.0),
    ],
)
def test_estimate_eta(done, expected, elapsed, eta):
    assert estimate_eta(done, expected, elapsed) == eta

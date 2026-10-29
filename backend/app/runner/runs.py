"""既存のランを元に新しいランを作る（DESIGN_research_features.md §4.2）。

- コピーするのは「出力と生成物を除いたもの全部」。入力の種類はランごとに違いうるので、入力を列挙せず出力を除外する
- 書き込むのは新しいランのディレクトリの中だけ。作成先は元ランと同じ親ディレクトリで、データルートの配下に限る
- 途中で失敗しても中途半端なランを残さないよう、隠しディレクトリに作ってから名前を変える
"""

import datetime as dt
import fnmatch
import hashlib
import json
import os
import re
import shutil
import uuid
from pathlib import Path

from app.errors import AccessDeniedError, ConflictError, InvalidInputError, NotFoundError
from app.models.runs import (
    CopyEntry,
    CreatedRun,
    EcoConstantModel,
    ExcludedEntry,
    InputLineModel,
    NewRunSpec,
    RunChange,
    RunPreview,
    RunTemplate,
)
from app.parsers.input_parser import InputParseError, parse_input_dat, source_reads_fkm_in
from app.runner.compile_command import default_compile_command, parse_compile_command
from app.runner.editors import (
    Locks,
    apply_eco_edits,
    apply_input_edits,
    parse_eco_constants,
    parse_input_lines,
)
from app.services.path_policy import PathNotAllowedError, resolve_within_data_roots

RECORD_FILE = "simviz_run.json"
LOG_FILE = "simviz_run.log"

# どの階層でも除外するもの（名前のパターン → 理由）
_EXCLUDE_PATTERNS: list[tuple[str, str]] = [
    ("*.out", "実行ファイル（作り直す）"),
    ("*.out.*", "実行ファイルの控え（a.out.bak_before_fix など）"),
    ("*.dSYM", "デバッグ情報（作り直す）"),
    ("*.exe", "実行ファイル（作り直す）"),
    ("*.obj", "コンパイル生成物"),
    ("*.o", "コンパイル生成物"),
    ("*.mod", "コンパイル生成物"),
    ("fort.*", "計算の出力（装置番号のファイル）"),
    ("*.xlsx", "表計算・発表資料"),
    ("*.xls", "表計算・発表資料"),
    ("*.pptx", "表計算・発表資料"),
    ("*.docx", "表計算・発表資料"),
    (RECORD_FILE, "元ランの記録"),
    (LOG_FILE, "元ランの記録"),
]

# open(..., file='名前', ..., status='replace') の形で書き出されるファイル（ソースから求める）
_OPEN_RE = re.compile(r"open\s*\(([^)]*)\)", re.I)
_FILE_ARG_RE = re.compile(r"file\s*=\s*['\"]\s*([^'\"]+?)\s*['\"]", re.I)
_REPLACE_RE = re.compile(r"status\s*=\s*['\"]replace['\"]", re.I)

_NAME_RE = re.compile(r"^[^/\\\0]+$")
_VERSIONED_RE = re.compile(r"^(?P<prefix>.*_v)(?P<n>\d+)$")


def _replaced_output_files(base: Path) -> set[str]:
    names: set[str] = set()
    for src in base.glob("*.f90"):
        text = src.read_text(encoding="utf-8", errors="replace")
        for m in _OPEN_RE.finditer(text):
            args = m.group(1)
            file_m = _FILE_ARG_RE.search(args)
            if file_m and _REPLACE_RE.search(args):
                names.add(file_m.group(1))
    return names


def _read_input(base: Path) -> str:
    path = base / "input.dat"
    if not path.is_file():
        raise InvalidInputError("元のランに input.dat がありません")
    return path.read_text(encoding="utf-8", errors="replace")


def _with_fkm_in(base: Path) -> bool:
    source = base / "mecnest.f90"
    return source_reads_fkm_in(source.read_text(encoding="utf-8", errors="replace")) if source.is_file() else True


def _parse_base_input(base: Path, input_text: str):
    try:
        return parse_input_dat(input_text, with_fkm_in=_with_fkm_in(base))
    except InputParseError as e:
        raise InvalidInputError(f"元のランの input.dat を解析できません: {e}") from e


def _result_dirs(base: Path, input_text: str) -> set[str]:
    parsed = _parse_base_input(base, input_text)
    return {parsed.result_dirs["hist"], parsed.result_dirs["field1"], parsed.result_dirs["field2"], "field3"}


def _structural_locks(base: Path, input_text: str) -> Locks:
    """格子寸法（in,jn,kn,nest）と地点（nhist・ijhist0）の値は変更させない。

    格子寸法はデータファイルや param.h と、地点数は地点の座標の数と食い違うと、
    作成時の検査をすり抜けて計算の実行まで失敗に気づけないため。histout（hist の出力間隔）は変更できる。
    """
    roles = _parse_base_input(base, input_text).line_roles
    locks: Locks = {roles["dims"]: None, roles["nhist"]: {0}}
    if "ijhist" in roles:
        locks[roles["ijhist"]] = None
    return locks


def plan_copy(base: Path, input_text: str) -> tuple[list[CopyEntry], list[ExcludedEntry], set[str]]:
    """コピーするもの・しないものを決める。3つ目は空で作り直す出力ディレクトリ。"""
    result_dirs = _result_dirs(base, input_text)
    replaced = _replaced_output_files(base)
    copy: list[CopyEntry] = []
    excluded: list[ExcludedEntry] = []

    def reason_for(rel: Path, is_top: bool) -> str | None:
        name = rel.name
        if name.startswith("."):
            return "隠しファイル"
        if is_top and name in result_dirs:
            return "出力ディレクトリ（中身はコピーせず空で作る）"
        if is_top and name in replaced:
            return "計算の出力（ソースで status='replace' で書き出すファイル）"
        for pattern, reason in _EXCLUDE_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return reason
        return None

    for current, dirnames, filenames in os.walk(base, followlinks=False):
        current_path = Path(current)
        is_top = current_path == base
        kept_dirs = []
        for d in sorted(dirnames):
            rel = (current_path / d).relative_to(base)
            if (current_path / d).is_symlink():
                excluded.append(ExcludedEntry(path=str(rel), reason="シンボリックリンク"))
            elif reason := reason_for(rel, is_top):
                excluded.append(ExcludedEntry(path=str(rel), reason=reason))
            else:
                kept_dirs.append(d)
                copy.append(CopyEntry(path=str(rel), bytes=0, is_dir=True))
        dirnames[:] = kept_dirs
        for f in sorted(filenames):
            full = current_path / f
            rel = full.relative_to(base)
            if full.is_symlink():
                excluded.append(ExcludedEntry(path=str(rel), reason="シンボリックリンク"))
            elif reason := reason_for(rel, is_top):
                excluded.append(ExcludedEntry(path=str(rel), reason=reason))
            else:
                copy.append(CopyEntry(path=str(rel), bytes=full.stat().st_size, is_dir=False))
    return copy, excluded, result_dirs


def _resolve_base(base_dir: str) -> Path:
    try:
        base = Path(resolve_within_data_roots(base_dir))
    except PathNotAllowedError:
        raise AccessDeniedError("許可されたデータディレクトリの外にはアクセスできません") from None
    if not base.is_dir():
        raise NotFoundError("元のランが見つかりません")
    return base


def default_run_name(base: Path) -> str:
    """元ランの隣で使われていない名前。`…_v16` なら同じ接頭辞の最大番号 +1、それ以外は `…_v2` から。"""
    siblings = {p.name for p in base.parent.iterdir()}
    m = _VERSIONED_RE.match(base.name)
    prefix = m.group("prefix") if m else f"{base.name}_v"
    numbers = [int(mm.group("n")) for s in siblings if (mm := _VERSIONED_RE.match(s)) and mm.group("prefix") == prefix]
    n = max(numbers, default=1) + 1
    while f"{prefix}{n}" in siblings:
        n += 1
    return f"{prefix}{n}"


def get_template(base_dir: str) -> RunTemplate:
    base = _resolve_base(base_dir)
    input_text = _read_input(base)
    copy, excluded, _ = plan_copy(base, input_text)
    eco_path = base / "eco.h"
    eco_text = eco_path.read_text(encoding="utf-8", errors="replace") if eco_path.is_file() else ""
    return RunTemplate(
        base_dir=str(base),
        default_name=default_run_name(base),
        default_compile_command=default_compile_command(base),
        input_lines=[
            InputLineModel(**vars(line)) for line in parse_input_lines(input_text, _structural_locks(base, input_text))
        ],
        eco_constants=[EcoConstantModel(**vars(c)) for c in parse_eco_constants(eco_text)],
        copy_entries=copy,
        excluded=excluded,
        copy_bytes=sum(e.bytes for e in copy),
    )


def _target_dir(base: Path, name: str) -> Path:
    if not _NAME_RE.match(name) or name in (".", "..") or name.startswith(".") or len(name) > 100:
        raise InvalidInputError("ランの名前に使えない文字が含まれています（/ や先頭の . は使えません）")
    target = base.parent / name
    try:
        resolve_within_data_roots(str(target))
    except PathNotAllowedError:
        raise AccessDeniedError("許可されたデータディレクトリの外には作れません") from None
    if target.exists():
        raise ConflictError(f"同じ名前のランが既にあります: {name}")
    return target


def _edited_files(base: Path, spec: NewRunSpec) -> tuple[str, str | None, list[RunChange]]:
    """編集後の input.dat・eco.h の内容と、変更点の一覧を作る（ファイルには書かない）。"""
    input_text = _read_input(base)
    locks = _structural_locks(base, input_text)
    lines = {line.line_no: line for line in parse_input_lines(input_text, locks)}
    for e in spec.input_edits:
        if e.line_no not in lines:
            raise InvalidInputError(f"input.dat に {e.line_no} 行目の値はありません")
    # 元と同じ値の「編集」は変更として数えない
    input_edits = {e.line_no: e.tokens for e in spec.input_edits if e.tokens != lines[e.line_no].tokens}
    new_input = apply_input_edits(input_text, input_edits, locks)
    # 書き換えた結果が、このランのソースの版の input.dat として読めることを確かめる
    try:
        parse_input_dat(new_input, with_fkm_in=_with_fkm_in(base))
    except InputParseError as e:
        raise InvalidInputError(f"変更後の input.dat を解析できません: {e}") from e

    changes = [
        RunChange(
            file="input.dat",
            where=f"{n}行目" + (f"（{lines[n].comment}）" if lines[n].comment else ""),
            before=" ".join(lines[n].tokens),
            after=" ".join(tokens),
        )
        for n, tokens in sorted(input_edits.items())
    ]

    new_eco = None
    if spec.eco_edits:
        eco_path = base / "eco.h"
        if not eco_path.is_file():
            raise InvalidInputError("元のランに eco.h がありません")
        eco_text = eco_path.read_text(encoding="utf-8", errors="replace")
        constants = {c.name.lower(): c for c in parse_eco_constants(eco_text)}
        eco_edits = {
            e.name: e.value.strip()
            for e in spec.eco_edits
            if e.name.lower() not in constants or constants[e.name.lower()].value != e.value.strip()
        }
        new_eco = apply_eco_edits(eco_text, eco_edits)
        changes += [
            RunChange(file="eco.h", where=name, before=constants[name.lower()].value, after=value)
            for name, value in eco_edits.items()
        ]
    return new_input, new_eco, changes


def preview(base_dir: str, spec: NewRunSpec) -> RunPreview:
    base = _resolve_base(base_dir)
    target = _target_dir(base, spec.name)
    parse_compile_command(spec.compile_command, base)
    _, _, changes = _edited_files(base, spec)
    copy, excluded, _ = plan_copy(base, _read_input(base))
    return RunPreview(
        target_dir=str(target),
        changes=changes,
        copy_count=sum(1 for e in copy if not e.is_dir),
        copy_bytes=sum(e.bytes for e in copy),
        excluded=excluded,
    )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_run(base_dir: str, spec: NewRunSpec) -> CreatedRun:
    base = _resolve_base(base_dir)
    target = _target_dir(base, spec.name)
    parse_compile_command(spec.compile_command, base)
    new_input, new_eco, changes = _edited_files(base, spec)
    copy, _, result_dirs = plan_copy(base, _read_input(base))

    staging = base.parent / f".{spec.name}.creating-{uuid.uuid4().hex[:8]}"
    try:
        staging.mkdir()
        for entry in copy:
            src, dst = base / entry.path, staging / entry.path
            if entry.is_dir:
                dst.mkdir(exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
        for d in sorted(result_dirs):
            (staging / d).mkdir(exist_ok=True)
        (staging / "input.dat").write_text(new_input, encoding="utf-8")
        if new_eco is not None:
            (staging / "eco.h").write_text(new_eco, encoding="utf-8")

        # 「どの設定とどのコードで作った結果か」を後から辿れるようにする
        record = {
            "schema": 1,
            "created_at": dt.datetime.now(dt.UTC).isoformat(),
            "base_run": str(base),
            "name": spec.name,
            "changes": [c.model_dump() for c in changes],
            "compile_command": spec.compile_command,
            "source_sha256": {
                p.name: _sha256(p) for p in sorted(staging.iterdir()) if p.suffix in (".f90", ".h") and p.is_file()
            },
            "status": "created",
        }
        (staging / RECORD_FILE).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return CreatedRun(path=str(target), changes=changes, record_file=str(target / RECORD_FILE))

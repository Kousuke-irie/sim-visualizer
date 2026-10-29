"""コンパイルコマンドの検査（DESIGN_research_features.md §4.4）。

ブラウザから受け取った文字列をそのままシェルに渡すと任意のコマンドが実行できてしまう。
先頭が gfortran で、引数は許可したフラグ・出力名・そのランの中の .f90 だけ、という形に限り、
シェルを介さず引数の配列として実行する。
"""

import re
import shlex
from pathlib import Path

from app.errors import InvalidInputError

# eco2.f90 は eco.f90 の古い版で、どのランにも並んでいる（同じ subroutine eco / atten を定義する）。
# 両方をリンクすると duplicate symbol で失敗するので既定には入れない（R6 で実際のランを動かして判明）
DEFAULT_SOURCES = ("mecnest.f90", "amamo.f90", "eco.f90")

_FLAG_RE = re.compile(r"^-(O[0-3s]?|g|f[\w-]+(=[\w.-]+)?|m[\w-]+(=[\w.-]+)?|std=\w+|W[\w-]*|cpp)$")
_NAME_RE = re.compile(r"^[\w.-]+$")
# subroutine / function の定義行。「end subroutine eco」や「call eco」、コメントは定義ではない
_ROUTINE_RE = re.compile(
    r"^\s*(?:(?:recursive|pure|elemental|integer|logical|real(?:\*\d+)?|double\s+precision)\s+)*"
    r"(?:subroutine|function)\s+(\w+)",
    re.I,
)


def default_compile_command(run_dir: Path) -> str:
    sources = [s for s in DEFAULT_SOURCES if (run_dir / s).is_file()]
    return " ".join(["gfortran", "-O2", "-o", "a.out", *sources])


def _defined_routines(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return {m.group(1).lower() for line in text.splitlines() if (m := _ROUTINE_RE.match(line))}


def _check_duplicate_routines(sources: list[str], run_dir: Path) -> None:
    """同じ名前のサブルーチンを定義するソースが2つあれば、待ち行列に入れる前に指摘する。

    gfortran はリンクの段階で初めて duplicate symbol で失敗し、ログを見るまで原因が分からないため。
    """
    seen: dict[str, str] = {}
    clashes: dict[tuple[str, str], set[str]] = {}
    for source in sources:
        for name in _defined_routines(run_dir / source):
            if name in seen and seen[name] != source:
                clashes.setdefault((seen[name], source), set()).add(name)
            seen.setdefault(name, source)
    if clashes:
        (first, second), names = next(iter(clashes.items()))
        raise InvalidInputError(
            f"{first} と {second} の両方に同じサブルーチンがあります（{', '.join(sorted(names))}）。"
            "どちらか一方だけをコンパイルコマンドに指定してください"
        )


def parse_compile_command(command: str, run_dir: Path) -> list[str]:
    """許可された形なら引数の配列を返し、そうでなければ InvalidInputError。"""
    try:
        argv = shlex.split(command)
    except ValueError as e:
        raise InvalidInputError(f"コンパイルコマンドを解釈できません: {e}") from e
    if not argv or argv[0] != "gfortran":
        raise InvalidInputError("コンパイルコマンドは gfortran で始めてください")

    sources = []
    output = None
    args = iter(argv[1:])
    for arg in args:
        if arg == "-o":
            output = next(args, None)
            if output is None or not _NAME_RE.match(output) or output.startswith("."):
                raise InvalidInputError("-o の出力名には、ディレクトリを含まないファイル名を指定してください")
        elif arg.startswith("-"):
            if not _FLAG_RE.match(arg):
                raise InvalidInputError(f"コンパイルコマンドで使えないオプションです: {arg}")
        elif arg.endswith(".f90") and _NAME_RE.match(arg) and not arg.startswith("."):
            if not (run_dir / arg).is_file():
                raise InvalidInputError(f"ソースファイルが見つかりません: {arg}")
            sources.append(arg)
        else:
            raise InvalidInputError(
                f"コンパイルコマンドに指定できない引数です: {arg}（ランの中の .f90 だけを指定できます）"
            )
    if not sources:
        raise InvalidInputError("コンパイルするソース（.f90）を指定してください")
    if output is None:
        raise InvalidInputError("-o で実行ファイル名を指定してください")
    _check_duplicate_routines(sources, run_dir)
    return argv

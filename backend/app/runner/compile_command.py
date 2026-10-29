"""コンパイルコマンドの検査（DESIGN_research_features.md §4.4）。

ブラウザから受け取った文字列をそのままシェルに渡すと任意のコマンドが実行できてしまう。
先頭が gfortran で、引数は許可したフラグ・出力名・そのランの中の .f90 だけ、という形に限り、
シェルを介さず引数の配列として実行する（実行は R5）。
"""

import re
import shlex
from pathlib import Path

from app.errors import InvalidInputError

DEFAULT_SOURCES = ("mecnest.f90", "amamo.f90", "eco.f90", "eco2.f90")

_FLAG_RE = re.compile(r"^-(O[0-3s]?|g|f[\w-]+(=[\w.-]+)?|m[\w-]+(=[\w.-]+)?|std=\w+|W[\w-]*|cpp)$")
_NAME_RE = re.compile(r"^[\w.-]+$")


def default_compile_command(run_dir: Path) -> str:
    sources = [s for s in DEFAULT_SOURCES if (run_dir / s).is_file()]
    return " ".join(["gfortran", "-O2", "-o", "a.out", *sources])


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
    return argv

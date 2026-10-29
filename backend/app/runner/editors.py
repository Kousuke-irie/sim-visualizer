"""input.dat と eco.h の「値の部分だけ」を書き換える（DESIGN_research_features.md §4.2）。

コメントや空白などの書式は残し、新旧のファイルを diff で比べたときに変えた値だけが出るようにする。
"""

import re
from dataclasses import dataclass

from app.errors import InvalidInputError

# Fortran の数値表記（整数・実数・指数部 d/e）。input.dat の値と eco.h の data 文の値に使う
FORTRAN_NUMBER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([dDeE][+-]?\d+)?$")


def is_fortran_number(token: str) -> bool:
    return FORTRAN_NUMBER_RE.match(token) is not None


# ---------- input.dat ----------


@dataclass
class InputLine:
    line_no: int  # 1 始まりの物理行番号
    tokens: list[str]
    comment: str  # '#' 以降（無ければ空）
    editable: bool  # 数値だけの行で、変更できる値が1つ以上あるか
    locked: list[bool]  # 値ごとに、変更できないか（格子寸法・地点など）


def _split_comment(raw: str) -> tuple[str, str]:
    body, sep, comment = raw.partition("#")
    return body, (sep + comment) if sep else ""


# 変更させない値の指定: コメント・空行を除いた何番目の行の、何番目の値か（None は行の全部）
Locks = dict[int, set[int] | None]


def parse_input_lines(text: str, locks: Locks | None = None) -> list[InputLine]:
    """input.dat の空でない各行を、値のトークンとコメントに分ける。

    編集できるのは**値がすべて数値の行だけ**。ファイル名の行（data/depth.dat、出力先の hist / field2 など）は
    編集させない。出力先を書き換えられると、計算が新しいランの外へ書き出せてしまうため。
    さらに locks で指定した値（格子寸法・地点など）も変更させない。
    """
    locks = locks or {}
    lines: list[InputLine] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        body, comment = _split_comment(raw)
        tokens = body.split()
        if not tokens:
            continue
        numeric = all(is_fortran_number(t) for t in tokens)
        index = len(lines)  # コメント・空行を除いた行の中での番号（パーサの数え方と同じ）
        positions = locks.get(index, set())
        locked = [not numeric or positions is None or j in positions for j in range(len(tokens))]
        lines.append(
            InputLine(
                line_no=i,
                tokens=tokens,
                comment=comment.lstrip("#").strip(),
                editable=numeric and not all(locked),
                locked=locked,
            )
        )
    return lines


def apply_input_edits(text: str, edits: dict[int, list[str]], locks: Locks | None = None) -> str:
    """指定した行の値トークンだけを置き換える。トークン間の空白・コメントはそのまま残す。"""
    by_no = {line.line_no: line for line in parse_input_lines(text, locks)}
    raw_lines = text.splitlines(keepends=True)
    for line_no, new_tokens in edits.items():
        line = by_no.get(line_no)
        if line is None:
            raise InvalidInputError(f"input.dat に {line_no} 行目の値はありません")
        if not all(is_fortran_number(t) for t in line.tokens):
            raise InvalidInputError(f"input.dat の {line_no} 行目（ファイル名などの行）は変更できません")
        if len(new_tokens) != len(line.tokens):
            raise InvalidInputError(
                f"input.dat の {line_no} 行目は値の数を変えられません（{len(line.tokens)} 個 → {len(new_tokens)} 個）"
            )
        changed_locked = [
            j for j, (old, new) in enumerate(zip(line.tokens, new_tokens, strict=True)) if line.locked[j] and old != new
        ]
        if changed_locked:
            raise InvalidInputError(
                f"input.dat の {line_no} 行目（{line.comment or '構造を決める行'}）の"
                f"{', '.join(str(j + 1) for j in changed_locked)}番目の値は変更できません"
                "（格子寸法や地点を変えると、データやソースと食い違い、計算を実行するまで失敗に気づけないため）"
            )
        bad = [t for t in new_tokens if not is_fortran_number(t)]
        if bad:
            raise InvalidInputError(f"input.dat の {line_no} 行目に数値でない値があります: {', '.join(bad)}")

        raw = raw_lines[line_no - 1]
        body, comment = _split_comment(raw.rstrip("\r\n"))
        newline = raw[len(raw.rstrip("\r\n")) :]
        # 元のトークンの位置を左から順に置き換え、区切りの空白は残す
        out, pos = [], 0
        for old, new in zip(line.tokens, new_tokens, strict=True):
            start = body.index(old, pos)
            out.append(body[pos:start])
            out.append(new)
            pos = start + len(old)
        out.append(body[pos:])
        raw_lines[line_no - 1] = "".join(out) + comment + newline
    return "".join(raw_lines)


# ---------- eco.h ----------

# `data 名前/値/` の形の data 文（値が1つのもの）。配列の data 文（値がカンマ区切り）は対象外
_DATA_RE = re.compile(r"^(?P<head>\s*data\s+)(?P<name>\w+)(?P<mid>\s*/\s*)(?P<value>[^/,!]+?)(?P<tail>\s*/.*)$", re.I)


@dataclass
class EcoConstant:
    name: str
    value: str
    line_no: int


def parse_eco_constants(text: str) -> list[EcoConstant]:
    constants: list[EcoConstant] = []
    for i, raw in enumerate(text.splitlines(), start=1):
        if raw.lstrip().startswith("!"):
            continue
        m = _DATA_RE.match(raw)
        if m and is_fortran_number(m.group("value").strip()):
            constants.append(EcoConstant(name=m.group("name"), value=m.group("value").strip(), line_no=i))
    return constants


def apply_eco_edits(text: str, edits: dict[str, str]) -> str:
    """data 文の値だけを置き換える。名前は大文字小文字を区別しない（Fortran と同じ）。"""
    by_name = {c.name.lower(): c for c in parse_eco_constants(text)}
    raw_lines = text.splitlines(keepends=True)
    for name, value in edits.items():
        constant = by_name.get(name.lower())
        if constant is None:
            raise InvalidInputError(f"eco.h に定数 {name} の data 文がありません")
        value = value.strip()
        if not is_fortran_number(value):
            raise InvalidInputError(f"eco.h の {name} の値が Fortran の数値として正しくありません: {value}")
        raw = raw_lines[constant.line_no - 1]
        newline = raw[len(raw.rstrip("\r\n")) :]
        m = _DATA_RE.match(raw.rstrip("\r\n"))
        assert m is not None  # parse_eco_constants で見つかった行なので必ず一致する
        raw_lines[constant.line_no - 1] = (
            m.group("head") + m.group("name") + m.group("mid") + value + m.group("tail") + newline
        )
    return "".join(raw_lines)

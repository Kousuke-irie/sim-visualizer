"""Tecplot POINT形式 (.plt) パーサ。

TITLE / VARIABLES / ZONE ヘッダを自動パースし、変数名・格子寸法を
ハードコードせずに取得する。ヘッダはファイル先頭のみに置かれる前提で、
それ以降のデータ部はデコードせずに NumPy でまとめて数値化する。
"""

import io
import re
import warnings
from dataclasses import dataclass

import numpy as np

REQUIRED_COORD_VARS = ("X", "Y", "Z")


class PltParseError(ValueError):
    pass


@dataclass
class ParsedPlt:
    variables: list[str]
    dims: dict[str, int]
    grid: np.ndarray  # shape (K, J, I, nvar)


def _is_number(token: bytes) -> bool:
    try:
        float(token)
    except ValueError:
        return False
    return True


def _decode(raw: bytes) -> str:
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("latin-1")


def _split_header(content: bytes) -> tuple[list[str], int]:
    """先頭のヘッダ行（英字で始まる行）を取り出し、読み飛ばした物理行数を返す。

    Tecplot POINT 形式ではヘッダはファイル先頭にしか現れない。以前は約4万行のデータ行すべてで
    ヘッダかどうかを判定していたが、最初の数値行で打ち切ることでデータ部を丸ごと NumPy に渡せる。
    """
    header: list[str] = []
    pos = 0
    skipped = 0
    while pos < len(content):
        end = content.find(b"\n", pos)
        end = len(content) if end == -1 else end + 1
        line = content[pos:end].strip()
        if line and (not line[:1].isalpha() or _is_number(line.split(None, 1)[0])):
            # NaN / Infinity は英字で始まるが数値（計算が発散したときに Fortran が書き出す）
            break
        if line:
            header.append(_decode(line))
        pos = end
        skipped += 1
    return header, skipped


def _parse_header(lines: list[str]) -> tuple[list[str] | None, dict[str, int]]:
    variables: list[str] | None = None
    dims: dict[str, int] = {}
    for line in lines:
        upper = line.upper()
        if upper.startswith("VARIABLES"):
            after_eq = line.split("=", 1)[1] if "=" in line else line[len("VARIABLES") :]
            variables = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", after_eq)
        elif upper.startswith("ZONE"):
            m_i = re.search(r"I\s*=\s*(\d+)", upper)
            m_j = re.search(r"J\s*=\s*(\d+)", upper)
            m_k = re.search(r"K\s*=\s*(\d+)", upper)
            if not (m_i and m_j and m_k):
                raise PltParseError("ZONE行から格子寸法 (I, J, K) を取得できません")
            dims = {"I": int(m_i.group(1)), "J": int(m_j.group(1)), "K": int(m_k.group(1))}
        # TITLE などそれ以外のヘッダ行は使わない
    return variables, dims


def parse_plt_bytes(content: bytes) -> ParsedPlt:
    header, skipped_lines = _split_header(content)
    variables, dims = _parse_header(header)

    if not variables:
        raise PltParseError("VARIABLES行が見つかりません")
    missing_coords = [v for v in REQUIRED_COORD_VARS if v not in variables]
    if missing_coords:
        raise PltParseError(f"必須の座標変数が不足しています: {missing_coords}")
    if not dims:
        raise PltParseError("ZONE行が見つかりません")

    nvar = len(variables)
    try:
        # データ部はデコードせずバイト列のまま C 実装で一括変換する（scripts/bench_plt_parser.py で計測:
        # 行ごとに float() する方式と比べて約2.5倍速く、ピークメモリは約1/9）。
        # 空行は読み飛ばされ、行ごとに列数が違えば ValueError になる
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)  # データ行が無いときの警告。下で明示的にエラーにする
            data = np.loadtxt(io.BytesIO(content), dtype=np.float64, skiprows=skipped_lines, ndmin=2)
    except ValueError as e:
        raise PltParseError(f"データ行の数値変換に失敗しました: {e}") from e
    if data.size == 0:
        raise PltParseError("データ行が見つかりません")

    expected_points = dims["I"] * dims["J"] * dims["K"]
    if data.shape[0] != expected_points:
        raise PltParseError(f"データ点数が格子寸法と一致しません: 期待={expected_points} 実際={data.shape[0]}")
    if data.shape[1] != nvar:
        raise PltParseError(f"列数が変数数と一致しません: 変数数={nvar} 列数={data.shape[1]}")

    grid = data.reshape(dims["K"], dims["J"], dims["I"], nvar)
    return ParsedPlt(variables=variables, dims=dims, grid=grid)


def parse_plt_text(text: str) -> ParsedPlt:
    return parse_plt_bytes(text.encode("utf-8"))

"""Tecplot POINT形式 (.plt) パーサ。

TITLE / VARIABLES / ZONE ヘッダを自動パースし、変数名・格子寸法を
ハードコードせずに取得する。
"""

import re
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

REQUIRED_COORD_VARS = ("X", "Y", "Z")


class PltParseError(ValueError):
    pass


@dataclass
class ParsedPlt:
    variables: List[str]
    dims: Dict[str, int]
    grid: np.ndarray  # shape (K, J, I, nvar)


def parse_plt_text(text: str) -> ParsedPlt:
    variables: List[str] = None
    dims: Dict[str, int] = {}
    data_lines: List[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        upper = line.upper()

        if upper.startswith("TITLE"):
            continue

        if upper.startswith("VARIABLES"):
            after_eq = line.split("=", 1)[1] if "=" in line else line[len("VARIABLES"):]
            variables = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", after_eq)
            continue

        if upper.startswith("ZONE"):
            m_i = re.search(r"I\s*=\s*(\d+)", upper)
            m_j = re.search(r"J\s*=\s*(\d+)", upper)
            m_k = re.search(r"K\s*=\s*(\d+)", upper)
            if not (m_i and m_j and m_k):
                raise PltParseError("ZONE行から格子寸法 (I, J, K) を取得できません")
            dims = {"I": int(m_i.group(1)), "J": int(m_j.group(1)), "K": int(m_k.group(1))}
            continue

        data_lines.append(line)

    if not variables:
        raise PltParseError("VARIABLES行が見つかりません")
    missing_coords = [v for v in REQUIRED_COORD_VARS if v not in variables]
    if missing_coords:
        raise PltParseError(f"必須の座標変数が不足しています: {missing_coords}")
    if not dims:
        raise PltParseError("ZONE行が見つかりません")
    if not data_lines:
        raise PltParseError("データ行が見つかりません")

    nvar = len(variables)
    try:
        data = np.array(
            [[float(v) for v in line.split()] for line in data_lines],
            dtype=np.float64,
        )
    except ValueError as e:
        raise PltParseError(f"データ行の数値変換に失敗しました: {e}") from e

    expected_points = dims["I"] * dims["J"] * dims["K"]
    if data.shape[0] != expected_points:
        raise PltParseError(
            f"データ点数が格子寸法と一致しません: 期待={expected_points} 実際={data.shape[0]}"
        )
    if data.shape[1] != nvar:
        raise PltParseError(
            f"列数が変数数と一致しません: 変数数={nvar} 列数={data.shape[1]}"
        )

    grid = data.reshape(dims["K"], dims["J"], dims["I"], nvar)
    return ParsedPlt(variables=variables, dims=dims, grid=grid)


def parse_plt_bytes(content: bytes) -> ParsedPlt:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    return parse_plt_text(text)

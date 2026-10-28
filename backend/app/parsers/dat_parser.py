"""時系列データ (`.dat`) パーサ。

1行目のメタ情報（i=, j=, n=, h=）と2行目の列ヘッダ（time[sec] と深度ラベル）を
自動パースし、変数名（ファイル名由来）以外はハードコードしない。
"""

import re
from dataclasses import dataclass
from typing import Dict, List

import numpy as np

DEPTH_LABEL_RE = re.compile(r"^-?\d+(\.\d+)?m$")


class DatParseError(ValueError):
    pass


@dataclass
class ParsedDat:
    grid: Dict[str, float]  # {"i": .., "j": .., "n": .., "h": ..}
    depths: List[str]
    depth_values: List[float]
    times: np.ndarray  # shape (n_times,)
    values: np.ndarray  # shape (n_times, n_depths)


def _parse_grid_line(line: str) -> Dict[str, float]:
    grid: Dict[str, float] = {}
    for key in ("i", "j", "n", "h"):
        m = re.search(rf"\b{key}\s*=\s*(-?\d+(?:\.\d+)?)", line, re.IGNORECASE)
        if not m:
            raise DatParseError(f"1行目から '{key}=' を取得できません")
        grid[key] = float(m.group(1))
    return grid


def _parse_depth_header(line: str) -> List[str]:
    tokens = line.split()
    if len(tokens) < 2:
        raise DatParseError("2行目（列ヘッダ）から深度ラベルを取得できません")
    depths = tokens[1:]
    invalid = [d for d in depths if not DEPTH_LABEL_RE.match(d)]
    if invalid:
        raise DatParseError(f"深度ラベルの形式が不正です: {invalid}")
    return depths


def parse_dat_text(text: str) -> ParsedDat:
    lines = [line for line in text.splitlines() if line.strip()]
    if len(lines) < 3:
        raise DatParseError("ファイルの行数が不足しています（メタ情報・列ヘッダ・データ行が必要です）")

    grid = _parse_grid_line(lines[0])
    depths = _parse_depth_header(lines[1])
    depth_values = [float(d[:-1]) for d in depths]

    data_lines = lines[2:]
    try:
        rows = [[float(v) for v in line.split()] for line in data_lines]
    except ValueError as e:
        raise DatParseError(f"データ行の数値変換に失敗しました: {e}") from e

    expected_cols = len(depths) + 1
    bad_rows = [i for i, row in enumerate(rows) if len(row) != expected_cols]
    if bad_rows:
        raise DatParseError(
            f"データ行の列数が深度数と一致しません（期待={expected_cols}列）。不正な行: {bad_rows[:5]}"
        )

    data = np.array(rows, dtype=np.float64)
    times = data[:, 0]
    values = data[:, 1:]

    return ParsedDat(grid=grid, depths=depths, depth_values=depth_values, times=times, values=values)


def parse_dat_bytes(content: bytes) -> ParsedDat:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        text = content.decode("latin-1")
    return parse_dat_text(text)

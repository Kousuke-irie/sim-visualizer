"""field2/ (.plt) と hist/ (.dat) の実在ファイルを走査する。

命名規則は DESIGN_directory_mode.md 4節・5節に準拠。
"""

import os
import re
from dataclasses import dataclass

PLT_FRAME_RE = re.compile(r"^tec-(\d+)\.plt$")
HIST_FILE_RE = re.compile(r"^(?P<param>[A-Za-z0-9]+)-0*(?P<point>\d+)\.dat$")

# ディレクトリ参照UIで input.dat 探索時に降りない（無関係・肥大化しがちな）ディレクトリ名
IGNORED_SCAN_DIR_NAMES = {"node_modules", "__pycache__", ".git", ".venv", "venv", ".cache"}
INPUT_DAT_SEARCH_MAX_DEPTH = 4
# 深さ制限だけでは node_modules 等の横に広いディレクトリで大量の走査が発生しうるため、
# 訪問ディレクトリ数にも上限を設けて worst-case を保証する。
INPUT_DAT_SEARCH_MAX_VISITS = 1500


@dataclass
class PltFrameRaw:
    file: str
    index: int
    time_sec: float


@dataclass
class TimeseriesIndexRaw:
    params: list[str]
    by_param: dict[str, list[str]]


def contains_input_dat(
    path: str,
    max_depth: int = INPUT_DAT_SEARCH_MAX_DEPTH,
    max_visits: int = INPUT_DAT_SEARCH_MAX_VISITS,
) -> bool:
    """path 自身、またはその子孫ディレクトリ（max_depth階層まで）に input.dat が存在するか。

    深さ制限に加えて訪問ディレクトリ数の上限（max_visits）を設け、node_modules 等の
    横に広いディレクトリ配下でも走査が長時間化しないようにする。
    """
    root_depth = path.rstrip(os.sep).count(os.sep)
    visited = 0
    for current_dir, dirnames, filenames in os.walk(path, followlinks=False):
        visited += 1
        if visited > max_visits:
            return False
        if "input.dat" in filenames:
            return True
        depth = current_dir.rstrip(os.sep).count(os.sep) - root_depth
        if depth >= max_depth:
            dirnames[:] = []
            continue
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in IGNORED_SCAN_DIR_NAMES]
    return False


def scan_plt_frames(field2_dir: str, ifit2: float) -> list[PltFrameRaw]:
    frames: list[PltFrameRaw] = []
    for name in os.listdir(field2_dir):
        m = PLT_FRAME_RE.match(name)
        if not m:
            continue
        index = int(m.group(1))
        frames.append(PltFrameRaw(file=name, index=index, time_sec=index * ifit2))
    frames.sort(key=lambda f: f.index)
    return frames


def scan_hist_files(hist_dir: str) -> TimeseriesIndexRaw:
    by_param: dict[str, list[str]] = {}
    for name in os.listdir(hist_dir):
        m = HIST_FILE_RE.match(name)
        if not m:
            continue
        param = m.group("param")
        point = f"{int(m.group('point')):02d}"
        by_param.setdefault(param, [])
        if point not in by_param[param]:
            by_param[param].append(point)

    for points in by_param.values():
        points.sort()

    return TimeseriesIndexRaw(params=sorted(by_param.keys()), by_param=by_param)

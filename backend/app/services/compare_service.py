"""2ケース比較（DESIGN_research_features.md §3）。

差分 B−A は数値の計算なのでサーバーで行う。色（0 を中心にした対称な範囲など）は見た目なのでブラウザで決める。
"""

import math

import numpy as np

from app.errors import InvalidInputError, NotFoundError
from app.models.compare import (
    CompareCheckRequest,
    CompareCheckResponse,
    ComparePoint,
    CompareSectionRequest,
    CompareSectionResponse,
    CompareTimeseriesRequest,
    CompareTimeseriesResponse,
)
from app.models.directory import DirectorySectionDataRequest, DirectoryTimeseriesRequest
from app.parsers.plt_parser import ParsedPlt
from app.services import directory_service
from app.services.directory_store import DirectoryEntry, directory_store

COORD_VARS = ("X", "Y", "Z")


def _dims_label(dims: dict[str, int]) -> str:
    return f"{dims['I']}x{dims['J']}x{dims['K']}"


def _same_time(t1: float, t2: float) -> bool:
    return math.isclose(t1, t2, rel_tol=0.0, abs_tol=1e-6)


def _frame_index_at(entry: DirectoryEntry, time_sec: float, label: str) -> int:
    frame = next((f for f in entry.plt_frames if _same_time(f.time_sec, time_sec)), None)
    if frame is None:
        raise InvalidInputError(f"{label} に時刻 {time_sec:g} 秒のフレームがありません")
    return frame.index


def _coords(parsed: ParsedPlt) -> np.ndarray:
    idx = [parsed.variables.index(v) for v in COORD_VARS]
    return parsed.grid[..., idx]


def _require_same_grid(dir_a: str, a: DirectoryEntry, dir_b: str, b: DirectoryEntry) -> None:
    if a.plt_dims != b.plt_dims:
        raise InvalidInputError(
            f"格子寸法が異なるため比較できません: A={_dims_label(a.plt_dims)} B={_dims_label(b.plt_dims)}"
        )
    # 寸法が同じでも、領域や層の取り方が違えば同じ格子点は同じ場所を指さない。最初のフレームの座標で確かめる
    _, _, frame_a = directory_service.load_frame(dir_a, a.plt_frames[0].index)
    _, _, frame_b = directory_service.load_frame(dir_b, b.plt_frames[0].index)
    if not np.allclose(_coords(frame_a), _coords(frame_b), rtol=0.0, atol=1e-6):
        raise InvalidInputError("格子の座標（X, Y, Z）が異なるため比較できません")


def check(req: CompareCheckRequest) -> CompareCheckResponse:
    a = directory_store.get(req.dir_a)
    b = directory_store.get(req.dir_b)
    _require_same_grid(req.dir_a, a, req.dir_b, b)

    times_b = [f.time_sec for f in b.plt_frames]
    common_times = [f.time_sec for f in a.plt_frames if any(_same_time(f.time_sec, t) for t in times_b)]
    if not common_times:
        raise InvalidInputError("A と B に共通する出力時刻がありません")

    points_b = {(p.i, p.j): p.point for p in b.parsed_input.points}
    common_points = [
        ComparePoint(point_a=p.point, point_b=points_b[(p.i, p.j)], i=p.i, j=p.j)
        for p in a.parsed_input.points
        if (p.i, p.j) in points_b
    ]

    return CompareCheckResponse(
        common_variables=[v for v in a.plt_variables if v in b.plt_variables and v not in COORD_VARS],
        common_times=common_times,
        common_params=[p for p in a.ts_index.params if p in b.ts_index.params],
        common_points=common_points,
    )


def _to_array(values: list[list[float | None]]) -> np.ndarray:
    return np.array([[np.nan if v is None else v for v in row] for row in values], dtype=float)


def _to_nested_list(values: np.ndarray, valid: np.ndarray) -> list[list[float | None]]:
    out = values.astype(object)
    out[~valid] = None
    return out.tolist()


def get_section(req: CompareSectionRequest) -> CompareSectionResponse:
    a = directory_store.get(req.dir_a)
    b = directory_store.get(req.dir_b)
    _require_same_grid(req.dir_a, a, req.dir_b, b)

    def fetch(dir_id: str, entry: DirectoryEntry, label: str):
        return directory_service.get_section_data(
            DirectorySectionDataRequest(
                dir_id=dir_id,
                frame_index=_frame_index_at(entry, req.time_sec, label),
                plane=req.plane,
                slice_index=req.slice_index,
                variable=req.variable,
                include_vectors=req.include_vectors,
            )
        )

    section_a = fetch(req.dir_a, a, "A")
    section_b = fetch(req.dir_b, b, "B")

    diff = _to_array(section_b.values) - _to_array(section_a.values)  # どちらかが欠損（NaN）なら NaN
    valid = ~np.isnan(diff)
    diff_range = (float(diff[valid].min()), float(diff[valid].max())) if valid.any() else None

    return CompareSectionResponse(
        a=section_a,
        b=section_b,
        diff=_to_nested_list(diff, valid),
        diff_range=diff_range,
    )


def _point_at(entry: DirectoryEntry, i: int, j: int, label: str) -> str:
    point = next((p.point for p in entry.parsed_input.points if (p.i, p.j) == (i, j)), None)
    if point is None:
        raise NotFoundError(f"{label} には格子位置 ({i}, {j}) の hist 地点がありません")
    return point


def get_timeseries(req: CompareTimeseriesRequest) -> CompareTimeseriesResponse:
    a = directory_store.get(req.dir_a)
    b = directory_store.get(req.dir_b)
    point_a = _point_at(a, req.i, req.j, "A")
    point_b = _point_at(b, req.i, req.j, "B")
    return CompareTimeseriesResponse(
        point_a=point_a,
        point_b=point_b,
        a=directory_service.get_timeseries_data(
            DirectoryTimeseriesRequest(dir_id=req.dir_a, param=req.param, point=point_a)
        ),
        b=directory_service.get_timeseries_data(
            DirectoryTimeseriesRequest(dir_id=req.dir_b, param=req.param, point=point_b)
        ),
    )

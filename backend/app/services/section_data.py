"""断面データ抽出（矩形格子を前提に、指定断面をJSONとして返す）。

描画自体はフロントエンド（Plotly）側で行うため、ここでは
指定平面・指定スライスの値を抽出し欠損をマスクするだけに専念する。

X, Y, Z はそれぞれ I, J, K のみに依存する矩形格子であることを前提とし
（本アプリの対象データはすべて該当）、断面抽出後の配列は必ず
(v方向, h方向, nvar) の形状になるよう PLANE_CONFIG で揃えている。
"""

from typing import Dict, List, Optional, Tuple

import numpy as np

from app.config import MISSING_VALUE
from app.models.section import SectionDataRequest, SectionDataResponse
from app.services.store import PltEntry

# grid_axis: entry.grid の shape (K, J, I, nvar) のうち、固定するスライス軸のインデックス
PLANE_CONFIG = {
    "YZ": {"slice_axis": "I", "grid_axis": 2, "h": "Y", "v": "Z", "vec_h": "V", "vec_v": "W"},
    "XZ": {"slice_axis": "J", "grid_axis": 1, "h": "X", "v": "Z", "vec_h": "U", "vec_v": "W"},
    "XY": {"slice_axis": "K", "grid_axis": 0, "h": "X", "v": "Y", "vec_h": "U", "vec_v": "V"},
}

AXIS_COORD_VAR = {"I": "X", "J": "Y", "K": "Z"}


class SectionDataError(ValueError):
    pass


def _mask_missing(arr: np.ndarray) -> np.ma.MaskedArray:
    return np.ma.masked_where(np.isclose(arr, MISSING_VALUE), arr)


def _to_nested_list(masked: np.ma.MaskedArray) -> List[List[Optional[float]]]:
    mask = np.ma.getmaskarray(masked)
    data = masked.data
    return [[None if mask[i, j] else float(data[i, j]) for j in range(data.shape[1])] for i in range(data.shape[0])]


def extract_section_data(entry: PltEntry, req: SectionDataRequest) -> SectionDataResponse:
    cfg = PLANE_CONFIG[req.plane]
    idx_var: Dict[str, int] = {name: i for i, name in enumerate(entry.variables)}

    for name in (cfg["h"], cfg["v"], req.variable):
        if name not in idx_var:
            raise SectionDataError(f"変数 {name} がデータに存在しません")

    axis_size = entry.dims[cfg["slice_axis"]]
    if not (0 <= req.slice_index < axis_size):
        raise SectionDataError(f"slice_index は 0〜{axis_size - 1} の範囲で指定してください")

    grid = entry.grid
    sub = np.take(grid, req.slice_index, axis=cfg["grid_axis"])  # shape: (v_len, h_len, nvar)

    h_coords = sub[0, :, idx_var[cfg["h"]]].astype(float).tolist()
    v_coords = sub[:, 0, idx_var[cfg["v"]]].astype(float).tolist()

    values2d = _mask_missing(sub[..., idx_var[req.variable]].astype(float))
    if values2d.count() == 0:
        raise SectionDataError("この断面には有効なデータがありません")

    coord_var = AXIS_COORD_VAR[cfg["slice_axis"]]
    coord_idx = idx_var[coord_var]
    if cfg["slice_axis"] == "I":
        actual_coord = float(grid[0, 0, req.slice_index, coord_idx])
    elif cfg["slice_axis"] == "J":
        actual_coord = float(grid[0, req.slice_index, 0, coord_idx])
    else:
        actual_coord = float(grid[req.slice_index, 0, 0, coord_idx])

    vector_h = vector_v = None
    vector_h_label = vector_v_label = None
    if req.include_vectors and cfg["vec_h"] in idx_var and cfg["vec_v"] in idx_var:
        vh = sub[..., idx_var[cfg["vec_h"]]].astype(float)
        vv = sub[..., idx_var[cfg["vec_v"]]].astype(float)
        vmask = np.isclose(vh, MISSING_VALUE) | np.isclose(vv, MISSING_VALUE)
        vector_h = _to_nested_list(np.ma.masked_where(vmask, vh))
        vector_v = _to_nested_list(np.ma.masked_where(vmask, vv))
        vector_h_label = cfg["vec_h"]
        vector_v_label = cfg["vec_v"]

    value_range: Tuple[float, float] = (float(values2d.min()), float(values2d.max()))

    return SectionDataResponse(
        h_coords=h_coords,
        v_coords=v_coords,
        h_label=cfg["h"],
        v_label=cfg["v"],
        values=_to_nested_list(values2d),
        vector_h=vector_h,
        vector_v=vector_v,
        vector_h_label=vector_h_label,
        vector_v_label=vector_v_label,
        actual_coord=actual_coord,
        actual_index=req.slice_index,
        value_range=[value_range[0], value_range[1]],
    )

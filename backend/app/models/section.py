from typing import Literal

from app.models.base import ApiModel


class SectionDataRequest(ApiModel):
    file_id: str
    plane: Literal["XY", "XZ", "YZ"]
    slice_index: int
    variable: str
    include_vectors: bool = True


class SectionDataResponse(ApiModel):
    h_coords: list[float]
    v_coords: list[float]
    h_label: str
    v_label: str
    values: list[list[float | None]]  # [v][h]、欠損は None
    vector_h: list[list[float | None]] | None = None
    vector_v: list[list[float | None]] | None = None
    vector_h_label: str | None = None
    vector_v_label: str | None = None
    actual_coord: float
    actual_index: int
    value_range: tuple[float, float]  # 欠損を除いた (min, max)

from typing import List, Literal, Optional

from pydantic import BaseModel


class SectionDataRequest(BaseModel):
    file_id: str
    plane: Literal["XY", "XZ", "YZ"]
    slice_index: int
    variable: str
    include_vectors: bool = True


class SectionDataResponse(BaseModel):
    h_coords: List[float]
    v_coords: List[float]
    h_label: str
    v_label: str
    values: List[List[Optional[float]]]  # [v][h]、欠損は None
    vector_h: Optional[List[List[Optional[float]]]] = None
    vector_v: Optional[List[List[Optional[float]]]] = None
    vector_h_label: Optional[str] = None
    vector_v_label: Optional[str] = None
    actual_coord: float
    actual_index: int
    value_range: List[float]

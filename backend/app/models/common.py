from typing import Dict, List

from pydantic import BaseModel


class Dims(BaseModel):
    I: int  # noqa: E741  Tecplot の格子軸名に合わせる
    J: int
    K: int


class Coords(BaseModel):
    X: List[float]
    Y: List[float]
    Z: List[float]


class PltMeta(BaseModel):
    file_id: str
    kind: str = "plt"
    variables: List[str]
    dims: Dims
    coords: Coords
    value_ranges: Dict[str, List[float]]


class DatGrid(BaseModel):
    i: int
    j: int
    n: int
    h: float


class DatMeta(BaseModel):
    file_id: str
    kind: str = "dat"
    variable: str
    grid: DatGrid
    depths: List[str]
    depth_values: List[float]
    time_range: List[float]
    n_times: int

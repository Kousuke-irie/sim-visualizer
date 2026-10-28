from pydantic import BaseModel


class Dims(BaseModel):
    I: int  # noqa: E741  Tecplot の格子軸名に合わせる
    J: int
    K: int


class Coords(BaseModel):
    X: list[float]
    Y: list[float]
    Z: list[float]


class PltMeta(BaseModel):
    file_id: str
    kind: str = "plt"
    variables: list[str]
    dims: Dims
    coords: Coords
    value_ranges: dict[str, list[float]]


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
    depths: list[str]
    depth_values: list[float]
    time_range: list[float]
    n_times: int

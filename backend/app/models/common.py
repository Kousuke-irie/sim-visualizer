from typing import Annotated, Literal

from pydantic import Field

from app.models.base import ApiModel


class Dims(ApiModel):
    I: int  # noqa: E741  Tecplot の格子軸名に合わせる
    J: int
    K: int


class Coords(ApiModel):
    X: list[float]
    Y: list[float]
    Z: list[float]


class PltMeta(ApiModel):
    file_id: str
    kind: Literal["plt"] = "plt"
    variables: list[str]
    dims: Dims
    coords: Coords
    value_ranges: dict[str, tuple[float, float]]  # 変数ごとの (min, max)


class DatGrid(ApiModel):
    i: int
    j: int
    n: int
    h: float


class DatMeta(ApiModel):
    file_id: str
    kind: Literal["dat"] = "dat"
    variable: str
    grid: DatGrid
    depths: list[str]
    depth_values: list[float]
    time_range: tuple[float, float]  # (min, max)
    n_times: int


# /api/upload は拡張子で .plt / .dat を判定してどちらかを返す。kind で区別できるよう判別共用体にする
UploadedMeta = Annotated[PltMeta | DatMeta, Field(discriminator="kind")]

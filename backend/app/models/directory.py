from typing import Literal

from pydantic import BaseModel

from app.models.common import DatGrid, Dims
from app.models.section import SectionDataResponse


class ResultDirs(BaseModel):
    hist: str
    field1: str
    field2: str


class DirectoryInputMeta(BaseModel):
    ifit2: float
    endtime: float
    dt: float
    dx: float
    z_levels: list[float]
    nhist: int
    histout: float
    result_dirs: ResultDirs


class HistPoint(BaseModel):
    point: str
    i: int
    j: int
    n: int
    x: float | None = None
    y: float | None = None


class PltFrameMeta(BaseModel):
    file: str
    index: int
    time_sec: float


class TimeseriesIndex(BaseModel):
    params: list[str]
    by_param: dict[str, list[str]]


class DirectoryMeta(BaseModel):
    dir_id: str
    root: str
    input: DirectoryInputMeta
    points: list[HistPoint]
    plt_frames: list[PltFrameMeta]
    timeseries: TimeseriesIndex
    plt_variables: list[str]
    plt_dims: Dims


class DirectoryOpenRequest(BaseModel):
    path: str


class DirectoryBrowseEntry(BaseModel):
    name: str
    path: str
    has_input_dat: bool


class DirectoryBrowseResponse(BaseModel):
    path: str
    parent: str | None = None
    entries: list[DirectoryBrowseEntry]


class DirectorySectionDataRequest(BaseModel):
    dir_id: str
    frame_index: int
    plane: Literal["XY", "XZ", "YZ"]
    slice_index: int
    variable: str
    include_vectors: bool = True


class DirectorySectionDataResponse(SectionDataResponse):
    frame_index: int
    time_sec: float


class DirectoryTimeseriesRequest(BaseModel):
    dir_id: str
    param: str
    point: str


class DirectoryTimeseriesResponse(BaseModel):
    variable: str
    point: str
    grid: DatGrid
    depths: list[str]
    depth_values: list[float]
    times: list[float]
    values: list[list[float]]

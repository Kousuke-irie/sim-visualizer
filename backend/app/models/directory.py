from typing import Dict, List, Literal, Optional

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
    z_levels: List[float]
    nhist: int
    histout: float
    result_dirs: ResultDirs


class HistPoint(BaseModel):
    point: str
    i: int
    j: int
    n: int
    x: Optional[float] = None
    y: Optional[float] = None


class PltFrameMeta(BaseModel):
    file: str
    index: int
    time_sec: float


class TimeseriesIndex(BaseModel):
    params: List[str]
    by_param: Dict[str, List[str]]


class DirectoryMeta(BaseModel):
    dir_id: str
    root: str
    input: DirectoryInputMeta
    points: List[HistPoint]
    plt_frames: List[PltFrameMeta]
    timeseries: TimeseriesIndex
    plt_variables: List[str]
    plt_dims: Dims


class DirectoryOpenRequest(BaseModel):
    path: str


class DirectoryBrowseEntry(BaseModel):
    name: str
    path: str
    has_input_dat: bool


class DirectoryBrowseResponse(BaseModel):
    path: str
    parent: Optional[str] = None
    entries: List[DirectoryBrowseEntry]


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
    depths: List[str]
    depth_values: List[float]
    times: List[float]
    values: List[List[float]]

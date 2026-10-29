from typing import Literal

from app.models.base import ApiModel
from app.models.directory import DirectorySectionDataResponse


class CompareCheckRequest(ApiModel):
    dir_a: str
    dir_b: str


class ComparePoint(ApiModel):
    """A・B で同じ格子位置 (i, j) にある hist 地点の組。地点番号が同じでも位置が違えば組にしない。"""

    point_a: str
    point_b: str
    i: int
    j: int


class CompareCheckResponse(ApiModel):
    common_variables: list[str]  # 両方にある描画変数（座標 X, Y, Z を除く）
    common_times: list[float]  # 両方に出力がある時刻[秒]
    common_params: list[str]  # 両方にある hist のパラメータ
    common_points: list[ComparePoint]


class CompareSectionRequest(ApiModel):
    dir_a: str
    dir_b: str
    time_sec: float  # フレーム番号ではなく時刻で突き合わせる（出力間隔 ifit2 が違うランも比べられるように）
    plane: Literal["XY", "XZ", "YZ"]
    slice_index: int
    variable: str
    include_vectors: bool = True


class CompareSectionResponse(ApiModel):
    a: DirectorySectionDataResponse
    b: DirectorySectionDataResponse
    diff: list[list[float | None]]  # B − A。どちらかが欠損なら None
    diff_range: tuple[float, float] | None  # 差分の (min, max)。有効な点が無ければ None

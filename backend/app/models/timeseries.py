from typing import List

from pydantic import BaseModel


class TimeseriesDataResponse(BaseModel):
    times: List[float]  # 秒
    values: List[List[float]]  # shape (n_times, n_depths)

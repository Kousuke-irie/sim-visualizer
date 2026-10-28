from pydantic import BaseModel


class TimeseriesDataResponse(BaseModel):
    times: list[float]  # 秒
    values: list[list[float]]  # shape (n_times, n_depths)

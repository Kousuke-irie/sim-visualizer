from app.models.base import ApiModel


class TimeseriesDataResponse(ApiModel):
    times: list[float]  # 秒
    values: list[list[float]]  # shape (n_times, n_depths)

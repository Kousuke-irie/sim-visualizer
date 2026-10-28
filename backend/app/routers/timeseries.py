from fastapi import APIRouter, HTTPException

from app.models.timeseries import TimeseriesDataResponse
from app.services.store import store

router = APIRouter(prefix="/api/timeseries", tags=["timeseries"])


@router.get("/data/{file_id}", response_model=TimeseriesDataResponse)
async def get_timeseries_data(file_id: str) -> TimeseriesDataResponse:
    try:
        entry = store.get_dat_entry(file_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたfile_idが見つかりません")

    return TimeseriesDataResponse(times=entry.times.tolist(), values=entry.values.tolist())

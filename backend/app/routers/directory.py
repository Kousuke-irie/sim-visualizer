"""ディレクトリモードの API。処理は services/directory_*.py にあり、ここは入出力の受け渡しだけを行う。"""

from fastapi import APIRouter

from app.models.directory import (
    DirectoryBrowseResponse,
    DirectoryMeta,
    DirectoryOpenRequest,
    DirectorySectionDataRequest,
    DirectorySectionDataResponse,
    DirectoryTimeseriesRequest,
    DirectoryTimeseriesResponse,
)
from app.services import directory_browse, directory_service
from app.services.directory_store import directory_store

router = APIRouter(prefix="/api/directory", tags=["directory"])


@router.get("/browse", response_model=DirectoryBrowseResponse)
async def browse_directory(path: str | None = None) -> DirectoryBrowseResponse:
    return directory_browse.browse(path)


@router.post("/open", response_model=DirectoryMeta)
async def open_directory(req: DirectoryOpenRequest) -> DirectoryMeta:
    return directory_service.open_directory(req.path)


@router.get("/{dir_id}/meta", response_model=DirectoryMeta)
async def get_directory_meta(dir_id: str) -> DirectoryMeta:
    return directory_store.get_meta(dir_id)


@router.post("/section/data", response_model=DirectorySectionDataResponse)
async def get_directory_section_data(req: DirectorySectionDataRequest) -> DirectorySectionDataResponse:
    return directory_service.get_section_data(req)


@router.post("/timeseries/data", response_model=DirectoryTimeseriesResponse)
async def get_directory_timeseries_data(req: DirectoryTimeseriesRequest) -> DirectoryTimeseriesResponse:
    return directory_service.get_timeseries_data(req)

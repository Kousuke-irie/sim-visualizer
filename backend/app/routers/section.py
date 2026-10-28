from fastapi import APIRouter, HTTPException

from app.models.section import SectionDataRequest, SectionDataResponse
from app.services.section_data import SectionDataError, extract_section_data
from app.services.store import store

router = APIRouter(prefix="/api/section", tags=["section"])


@router.post("/data", response_model=SectionDataResponse)
async def get_section_data(req: SectionDataRequest) -> SectionDataResponse:
    try:
        entry = store.get_plt(req.file_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="指定されたfile_idが見つかりません") from None

    try:
        return extract_section_data(entry, req)
    except SectionDataError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

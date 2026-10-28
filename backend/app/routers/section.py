from fastapi import APIRouter

from app.models.section import SectionDataRequest, SectionDataResponse
from app.services.section_data import extract_section_data
from app.services.store import store

router = APIRouter(prefix="/api/section", tags=["section"])


@router.post("/data", response_model=SectionDataResponse)
async def get_section_data(req: SectionDataRequest) -> SectionDataResponse:
    return extract_section_data(store.get_plt(req.file_id), req)

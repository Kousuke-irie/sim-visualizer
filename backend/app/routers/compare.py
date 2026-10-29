"""2ケース比較の API。処理は services/compare_service.py にある。"""

from fastapi import APIRouter

from app.models.compare import CompareCheckRequest, CompareCheckResponse, CompareSectionRequest, CompareSectionResponse
from app.services import compare_service

router = APIRouter(prefix="/api/compare", tags=["compare"])


@router.post("/check", response_model=CompareCheckResponse)
async def check(req: CompareCheckRequest) -> CompareCheckResponse:
    return compare_service.check(req)


@router.post("/section", response_model=CompareSectionResponse)
async def section(req: CompareSectionRequest) -> CompareSectionResponse:
    return compare_service.get_section(req)

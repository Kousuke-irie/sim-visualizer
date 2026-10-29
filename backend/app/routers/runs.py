"""新しいランの作成 API（DESIGN_research_features.md §4）。処理はホストの runner が行う。"""

from fastapi import APIRouter

from app.models.runs import CreatedRun, CreateRunRequest, RunPreview, RunTemplate, RunTemplateRequest
from app.services import run_service

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("/template", response_model=RunTemplate)
async def template(req: RunTemplateRequest) -> RunTemplate:
    return run_service.get_template(req.dir_id)


@router.post("/preview", response_model=RunPreview)
async def preview(req: CreateRunRequest) -> RunPreview:
    return run_service.preview(req)


@router.post("", response_model=CreatedRun)
async def create(req: CreateRunRequest) -> CreatedRun:
    return run_service.create(req)

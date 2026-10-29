"""新しいランの作成・計算の実行 API（DESIGN_research_features.md §4）。処理はホストの runner が行う。

runner への通信（urllib）は同期で、作成のコピーには数秒かかりうる。async def にするとその間イベントループが止まり、
可視化の要求まで待たされるので、通常の def にしてスレッドプールで動かす。
"""

from fastapi import APIRouter, Query

from app.models.jobs import Job, JobList, JobLog, SubmitJobRequest
from app.models.runs import CreatedRun, CreateRunRequest, RunPreview, RunTemplate, RunTemplateRequest
from app.services import run_service

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("/template", response_model=RunTemplate)
def template(req: RunTemplateRequest) -> RunTemplate:
    return run_service.get_template(req.dir_id)


@router.post("/preview", response_model=RunPreview)
def preview(req: CreateRunRequest) -> RunPreview:
    return run_service.preview(req)


@router.post("", response_model=CreatedRun)
def create(req: CreateRunRequest) -> CreatedRun:
    return run_service.create(req)


# 計算の待ち行列。ランはコンテナ内のパス（新しいランの作成結果の path）で指定する


@router.get("/jobs", response_model=JobList)
def list_jobs() -> JobList:
    return run_service.list_jobs()


@router.post("/jobs", response_model=Job)
def submit_job(req: SubmitJobRequest) -> Job:
    return run_service.submit_job(req.path)


@router.post("/jobs/{job_id}/cancel", response_model=Job)
def cancel_job(job_id: str) -> Job:
    return run_service.cancel_job(job_id)


@router.get("/jobs/{job_id}/log", response_model=JobLog)
def job_log(job_id: str, lines: int = Query(default=200, ge=1, le=2000)) -> JobLog:
    return run_service.job_log(job_id, lines)

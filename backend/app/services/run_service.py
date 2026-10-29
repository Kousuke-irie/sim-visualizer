"""新しいランの作成（/api/runs/*）。開いたディレクトリ（dir_id）を元ランとして、ホストの runner に依頼する。"""

from app.models.jobs import Job, JobList, JobLog
from app.models.runs import CreatedRun, CreateRunRequest, NewRunSpec, RunPreview, RunTemplate
from app.services import runner_client
from app.services.directory_store import directory_store


def _base_dir(dir_id: str) -> str:
    return runner_client.to_host_path(directory_store.get(dir_id).root)


def _spec_payload(req: CreateRunRequest) -> dict:
    return {"base_dir": _base_dir(req.dir_id), **NewRunSpec.model_validate(req.model_dump()).model_dump()}


def get_template(dir_id: str) -> RunTemplate:
    template = RunTemplate.model_validate(runner_client.call("/template", {"base_dir": _base_dir(dir_id)}))
    return template.model_copy(update={"base_dir": runner_client.to_container_path(template.base_dir)})


def preview(req: CreateRunRequest) -> RunPreview:
    result = RunPreview.model_validate(runner_client.call("/preview", _spec_payload(req)))
    return result.model_copy(update={"target_dir": runner_client.to_container_path(result.target_dir)})


def create(req: CreateRunRequest) -> CreatedRun:
    result = CreatedRun.model_validate(runner_client.call("/runs", _spec_payload(req)))
    return result.model_copy(
        update={
            "path": runner_client.to_container_path(result.path),
            "record_file": runner_client.to_container_path(result.record_file),
        }
    )


# ---- 計算の待ち行列（§4.3〜§4.5）----


def _job_to_container(job: dict) -> Job:
    parsed = Job.model_validate(job)
    return parsed.model_copy(
        update={
            "run_dir": runner_client.to_container_path(parsed.run_dir),
            "base_run": runner_client.to_container_path(parsed.base_run),
        }
    )


def submit_job(path: str) -> Job:
    return _job_to_container(runner_client.call("/jobs", {"run_dir": runner_client.to_host_path(path)}))


def list_jobs() -> JobList:
    body = runner_client.call("/jobs/list", {})
    return JobList(jobs=[_job_to_container(j) for j in body.get("jobs", [])])


def cancel_job(job_id: str) -> Job:
    return _job_to_container(runner_client.call("/jobs/cancel", {"job_id": job_id}))


def job_log(job_id: str, lines: int) -> JobLog:
    return JobLog.model_validate(runner_client.call("/jobs/log", {"job_id": job_id, "lines": lines}))

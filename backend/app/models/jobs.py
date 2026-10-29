"""計算の待ち行列（DESIGN_research_features.md §4.3・§4.5）の API スキーマ。runner とバックエンドで共通に使う。"""

from typing import Literal

from pydantic import Field

from app.models.base import ApiModel

# queued → compiling → running → succeeded / failed / cancelled。
# interrupted は、runner の停止中に計算が止まり、終わり方が分からなくなったもの
JobStatus = Literal["queued", "compiling", "running", "succeeded", "failed", "cancelled", "interrupted"]


class Job(ApiModel):
    job_id: str
    name: str
    run_dir: str
    base_run: str  # 元のラン（「元のランと比較」に使う）
    status: JobStatus
    message: str  # 失敗・中止の理由など
    created_at: str
    started_at: str | None
    finished_at: str | None
    exit_code: int | None
    frames_done: int  # 書き出された tec-*.plt の数
    frames_expected: int  # endtime / ifit2 + 1
    elapsed_sec: float | None
    eta_sec: float | None  # 終了までの見込み（2枚目が出るまでは不明）


class JobList(ApiModel):
    jobs: list[Job]


class JobLog(ApiModel):
    job_id: str
    text: str  # simviz_run.log の末尾
    truncated: bool  # 末尾だけを返したか


# ---- バックエンド（/api/runs/jobs）用：ランはコンテナ内のパスで指定する ----


class SubmitJobRequest(ApiModel):
    path: str


# ---- runner（ホスト）用 ----


class RunnerSubmitRequest(ApiModel):
    run_dir: str


class RunnerJobRequest(ApiModel):
    job_id: str


class RunnerLogRequest(ApiModel):
    job_id: str
    lines: int = Field(default=200, ge=1, le=2000)

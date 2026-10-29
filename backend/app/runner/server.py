"""runner の HTTP サーバー（ホストの 127.0.0.1 だけで待ち受ける）。

ブラウザから直接ではなく、Docker のバックエンドから呼ばれる。ホストでファイルを書き・コマンドを実行する口なので、
起動時に決めたトークン（環境変数 SIMVIZ_RUNNER_TOKEN、.env でバックエンドと共有）が無い要求はすべて拒否する。
"""

import os
import secrets

from fastapi import Depends, FastAPI, Header, HTTPException

from app.error_handlers import register_app_error_handler
from app.models.runs import CreatedRun, RunnerCreateRequest, RunnerTemplateRequest, RunPreview, RunTemplate
from app.runner import runs

TOKEN_ENV = "SIMVIZ_RUNNER_TOKEN"
TOKEN_HEADER = "X-SimViz-Token"


def require_token(x_simviz_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get(TOKEN_ENV, "")
    # トークンが未設定なら誰も通さない（空文字どうしの一致で素通りさせない）
    if not expected or not x_simviz_token or not secrets.compare_digest(x_simviz_token, expected):
        raise HTTPException(status_code=401, detail="runner への要求にはトークンが必要です")


app = FastAPI(title="Sim Visualizer runner", dependencies=[Depends(require_token)])
register_app_error_handler(app)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/template", response_model=RunTemplate)
def template(req: RunnerTemplateRequest) -> RunTemplate:
    return runs.get_template(req.base_dir)


@app.post("/preview", response_model=RunPreview)
def preview(req: RunnerCreateRequest) -> RunPreview:
    return runs.preview(req.base_dir, req)


@app.post("/runs", response_model=CreatedRun)
def create(req: RunnerCreateRequest) -> CreatedRun:
    return runs.create_run(req.base_dir, req)

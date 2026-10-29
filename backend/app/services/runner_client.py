"""ホストの runner への依頼（DESIGN_research_features.md §4.3）。

バックエンドは Docker の中で計算結果を読み取り専用でマウントしている。新しいランの作成・計算の実行は
ホストの runner に任せ、ここではパスの読み替え（/data/… ⇔ DATA_DIR/…）と通信・エラーの変換だけを行う。
依存を増やさないよう標準ライブラリの urllib で HTTP を送る。
"""

import json
import os
import urllib.error
import urllib.request
from collections.abc import Callable

from app.config import data_dir_mapping, runner_url
from app.errors import (
    AccessDeniedError,
    AppError,
    ConflictError,
    InvalidInputError,
    NotFoundError,
    ServiceUnavailableError,
)

TOKEN_ENV = "SIMVIZ_RUNNER_TOKEN"
TOKEN_HEADER = "X-SimViz-Token"
TIMEOUT_SECONDS = 120  # コピーは数百KB程度だが、ディスクが遅い場合に備えて長めにとる

START_HINT = (
    "再計算用の runner が起動していません。ホストのターミナルで "
    "`cd backend && set -a && . ../.env && set +a && .venv/bin/python -m app.runner` を実行してください"
)

_ERROR_BY_STATUS: dict[int, type[AppError]] = {
    400: InvalidInputError,
    403: AccessDeniedError,
    404: NotFoundError,
    409: ConflictError,
}


def to_host_path(path: str) -> str:
    mapping = data_dir_mapping()
    if mapping is None:
        return path
    container, host = mapping
    if path == container or path.startswith(container + "/"):
        return host + path[len(container) :]
    # データルートの外。runner 側の判定で拒否されるが、ここで読み替えずにそのまま渡す
    return path


def to_container_path(path: str) -> str:
    mapping = data_dir_mapping()
    if mapping is None:
        return path
    container, host = mapping
    if path == host or path.startswith(host + "/"):
        return container + path[len(host) :]
    return path


Send = Callable[[str, dict], tuple[int, dict]]


def _urllib_send(path: str, payload: dict) -> tuple[int, dict]:
    request = urllib.request.Request(
        runner_url() + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", TOKEN_HEADER: os.environ.get(TOKEN_ENV, "")},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as res:
            return res.status, json.loads(res.read() or b"{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read() or b"{}")
        except ValueError:
            body = {}
        return e.code, body
    except (urllib.error.URLError, ConnectionError, TimeoutError) as e:
        raise ServiceUnavailableError(START_HINT) from e


# テストでは runner のアプリを直接呼ぶ関数に差し替える
_send: Send = _urllib_send


def call(path: str, payload: dict) -> dict:
    status, body = _send(path, payload)
    if 200 <= status < 300:
        return body
    detail = body.get("detail") if isinstance(body.get("detail"), str) else f"runner がエラーを返しました（{status}）"
    if status == 401:
        raise ServiceUnavailableError("runner のトークンが一致しません。.env の SIMVIZ_RUNNER_TOKEN を確認してください")
    raise _ERROR_BY_STATUS.get(status, ServiceUnavailableError)(detail)

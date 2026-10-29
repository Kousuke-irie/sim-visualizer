"""runner を起動する: `python -m app.runner`（backend ディレクトリで、ホストの Python から）。

必要な環境変数（リポジトリ直下の .env に書き、`set -a; . ../.env; set +a` で読み込む）:
  SIMVIZ_RUNNER_TOKEN  バックエンドと共有するトークン
  SIMVIZ_DATA_ROOTS    計算結果の親ディレクトリ（ホスト上の絶対パス）。未設定なら DATA_DIR
                       （Docker が /data にマウントしているのと同じ場所）を使う
"""

import os
import sys

import uvicorn

from app.config import DATA_ROOTS_ENV
from app.runner.server import TOKEN_ENV, app

HOST = "127.0.0.1"  # 外部からは接続させない
DEFAULT_PORT = 8100


def main() -> None:
    if not os.environ.get(DATA_ROOTS_ENV) and os.environ.get("DATA_DIR"):
        os.environ[DATA_ROOTS_ENV] = os.path.abspath(os.environ["DATA_DIR"])
    missing = [name for name in (TOKEN_ENV, DATA_ROOTS_ENV) if not os.environ.get(name)]
    if missing:
        sys.exit(f"環境変数が設定されていません: {', '.join(missing)}（README の「再計算（runner）」を参照）")
    uvicorn.run(app, host=HOST, port=int(os.environ.get("SIMVIZ_RUNNER_PORT", DEFAULT_PORT)))


if __name__ == "__main__":
    main()

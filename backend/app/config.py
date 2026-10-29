import os

MISSING_VALUE = -999.0

SESSION_TTL_SECONDS = 6 * 60 * 60  # 6時間

CORS_ALLOW_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ディレクトリモードで参照・オープンを許可するデータルート（os.pathsep 区切りで複数可）。
# docker compose では計算結果を /data に読み取り専用でマウントする。Docker を使わずに起動する場合は
# この環境変数で計算結果の親ディレクトリを指定する（未指定時はサーバー上の任意パスを読ませない）。
DATA_ROOTS_ENV = "SIMVIZ_DATA_ROOTS"
DEFAULT_DATA_ROOTS = ["/data"]

# 実データの .plt は1ファイル約10MB。桁違いに大きいものは誤操作とみなし、メモリを使い切る前に拒否する
MAX_UPLOAD_BYTES = 100 * 1024 * 1024


def data_roots() -> list[str]:
    # テストや起動方法ごとに切り替えられるよう、import 時ではなく呼び出しのたびに読む
    raw = os.environ.get(DATA_ROOTS_ENV)
    if not raw:
        return list(DEFAULT_DATA_ROOTS)
    return [p for p in raw.split(os.pathsep) if p]


# ---- 再計算（ホストの runner）への依頼（DESIGN_research_features.md §4.3） ----
RUNNER_URL_ENV = "SIMVIZ_RUNNER_URL"  # docker compose では http://host.docker.internal:8100
DEFAULT_RUNNER_URL = "http://127.0.0.1:8100"
# コンテナ内のパス（/data/…）とホスト上のパス（DATA_DIR/…）の対応。未設定なら同じパスとして扱う（Docker なしの起動）
HOST_DATA_DIR_ENV = "SIMVIZ_HOST_DATA_DIR"
CONTAINER_DATA_DIR_ENV = "SIMVIZ_CONTAINER_DATA_DIR"
DEFAULT_CONTAINER_DATA_DIR = "/data"


def runner_url() -> str:
    return os.environ.get(RUNNER_URL_ENV, DEFAULT_RUNNER_URL).rstrip("/")


def data_dir_mapping() -> tuple[str, str] | None:
    """(コンテナ内の接頭辞, ホスト上の接頭辞)。対応づけが要らなければ None。"""
    host = os.environ.get(HOST_DATA_DIR_ENV)
    if not host:
        return None
    container = os.environ.get(CONTAINER_DATA_DIR_ENV, DEFAULT_CONTAINER_DATA_DIR)
    return container.rstrip("/"), host.rstrip("/")

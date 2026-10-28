"""FastAPI の OpenAPI スキーマを JSON に書き出す。

フロントエンドの TypeScript 型（frontend/src/types/api.gen.ts）はこのファイルから生成する。
Pydantic モデルを変えたら、このスクリプトと `npm run gen:api` を実行して両方コミットする。
CI は再生成して差分が出ないことを確認する。

    python scripts/export_openapi.py [出力先]   # 既定: ../frontend/openapi.json
"""

import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app  # noqa: E402  sys.path を通してから import する

DEFAULT_OUTPUT = BACKEND_DIR.parent / "frontend" / "openapi.json"


def main() -> None:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    # 差分レビューと CI の比較を安定させるため、キー順を固定し、日本語はエスケープしない
    text = json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    output.write_text(text, encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()

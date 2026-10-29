# CLAUDE.md — LLM（AI コーディングエージェント）向け開発ルール

このリポジトリで AI エージェントが作業するときのルール。人間の開発者にもそのまま適用する。
仕様・設計の正は [DESIGN.md](DESIGN.md) / [DESIGN_directory_mode.md](DESIGN_directory_mode.md)、使い方は [README.md](README.md)。

## 1. 役割分担（最重要）

- **判断するのは人間、AI は提案と実装を担当する。** 次のことは、実装前に必ず人間に確認する。
  - 設計方針の変更（責務の分け方、API の形、データモデル）
  - 機能の追加・削除、UI レイアウトの変更
  - 依存ライブラリの追加・メジャーバージョンアップ
  - 外部に公開される操作（push、リポジトリ・Issue・PR の作成、公開設定の変更）
- 選択肢があるときは、全部を並べるのではなく推奨案と理由を示す。
- 指示が曖昧なら、推測で大きく作らず、まず小さく確認する。

## 2. 守るべき設計原則（破るときは DESIGN.md を先に更新）

1. **データと見た目の分離。** サーバーへのリクエストに描画スタイル（色、レベル数、ラベル、ベクトルの見た目など）を含めない。
   サーバーは生の数値だけを返し、描画はブラウザ（Plotly.js）で行う。見た目の変更で `/api` 通信が発生したらバグ
   （`frontend/e2e/section.spec.ts` で検証している）。
2. **データ形式をハードコードしない。** 変数名・格子寸法・出力ディレクトリ名はファイル（`.plt` ヘッダ、`input.dat`）から読む。
   `input.dat` の理論値より、実在するファイルを正とする。
3. **未対応のものは黙って誤動作させず、明示的にエラーにする。** 例: `nest>1`、負の `fifit2`。
   パーサは専用の例外 → ルーターで 4xx の `HTTPException`（日本語の detail）に変換する。
4. **バックエンドは単一ワーカー前提。** ストアはインメモリなので `uvicorn --workers` を増やさない。
5. **サーバー上のパスはデータルート配下に限定する。** ファイルを開く処理を追加するときは、ユーザー入力でも
   データファイルの中身でも、必ず `services/path_policy.py` を通す。
6. **ホストへの書き込みとコマンド実行は runner だけが行う。** バックエンドは計算結果を読み取り専用で扱い、
   runner は新しいランのディレクトリの中にだけ書く。実行してよいのは gfortran と新しいランの実行ファイルだけで、
   シェルを介さず引数の配列で起動する（`app/runner/compile_command.py`）。ブラウザからの文字列をシェルに渡さない。
7. **研究データ・個人情報をコミットしない。** `data/`、`.env`、`PORTFOLIO.md`、`.claude/settings.local.json` は `.gitignore` 済み。
   テストデータは `backend/app/tests/sample_data.py` の合成データを使う。

## 3. 作業の進め方

- **作業は Git のブランチで行う。** main へ直接コミットしない（`feat/…`、`fix/…`、`refactor/…`、`test/…`）。
- **テストが先、リファクタは後。** 振る舞いを変えないリファクタは、先にテストで振る舞いを固定してから行う。
- **1コミット1目的。** 整形だけの変更とロジックの変更は混ぜない。
- **バグ修正には回帰テストを付ける。** 再現するテストを先に書き、失敗することを確かめてから直す。
- **計測してから最適化する。** パフォーマンス改善は、変更前後のベンチマーク値をコミットメッセージか PR に残す。
- **設計を変えたら DESIGN.md も同じ PR で更新する。** 判断の理由（なぜそうしたか、何を捨てたか）も書く。
- 書式は Prettier（frontend）と ruff format（backend）に任せ、手で整えない。`eslint-disable` は理由をコメントに書ける場合だけ使う。
- ファイル内の既存のスタイル（命名、日本語コメントの密度、イディオム）に合わせる。
  コメントには「何をしているか」ではなく「なぜそうしているか」を書く。

## 4. 完了の定義（変更をコミットする前に、全部通すこと）

```bash
# backend
cd backend
.venv/bin/ruff check app scripts && .venv/bin/ruff format --check app scripts
.venv/bin/pytest

# frontend
cd frontend
npm run lint && npm run format:check && npm run typecheck && npm test && npm run build

# UI や API に触れた場合は E2E も
PYTHON="$PWD/../backend/.venv/bin/python" npm run e2e
```

- テストが失敗したまま「完了」と報告しない。スキップしたテスト・未確認の項目があれば、そのことを明記する。
- テストを通すためにテストを弱めない（期待値の書き換え、`skip`）。必要なら理由を説明して人間に確認する。
- CI（`.github/workflows/ci.yml`）は上と同じ内容を実行する。CI が赤のまま次の作業に進まない。

## 5. コード配置の約束

| 層 | 置き場所 | ルール |
|---|---|---|
| パーサ | `backend/app/parsers/` | 外部ファイル形式の解釈のみ。FastAPI に依存しない。専用の例外を投げる |
| サービス | `backend/app/services/` | 業務処理（ファイル読み込み・抽出・キャッシュ・ストア）。HTTP を知らず、失敗は `app/errors.py` の業務エラー（日本語の detail）で投げる |
| ルーター | `backend/app/routers/` | リクエストをサービスに渡して結果を返すだけ。`HTTPException` は使わない（業務エラー → ステータスの変換は `main.py` の例外ハンドラ1か所） |
| モデル | `backend/app/models/` | Pydantic スキーマ（`ApiModel` を継承）。変更したら `python scripts/export_openapi.py` → `npm run gen:api` で TS 型を再生成してコミットする（CI が鮮度を検査）。`api.gen.ts` は手で編集しない |
| 描画ロジック | `frontend/src/components/**/*Figure.ts` など | React に依存しない純粋関数にして Vitest でテストする |
| コンポーネント | `frontend/src/components/` | 状態管理と表示のみ。計算はロジック側に寄せる |
| テスト | `backend/app/tests/`、`frontend/src/**/*.test.ts`、`frontend/e2e/` | 合成データは `sample_data.py` に集約する |

## 6. ローカル実行のヒント

- 通常は `docker compose up`（http://localhost:5173）。`DATA_DIR` は `.env` で指定する。
- Docker を使わずにバックエンドを起動するときは、`SIMVIZ_DATA_ROOTS=<計算結果の親ディレクトリ>` を指定する
  （未指定だと `/data` 以外は開けない。DESIGN_directory_mode.md 2.1）。
- 新しいランの作成は**ホストの runner**（`cd backend && set -a && . ../.env && set +a && .venv/bin/python -m app.runner`）が行う。
  E2E は runner も自動で起動する（ポート 8101・専用トークン）。
- Docker を使わずに Vite を起動するときは `API_PROXY_TARGET=http://127.0.0.1:8000 npm run dev`。
  `vite.config.ts` を一時的に書き換える必要はない（DESIGN.md 17-4 / 18-4 に書いた回避策はもう不要）。
- 動作確認用の計算結果ディレクトリは `cd backend && .venv/bin/python -m app.tests.sample_data <出力先>` で作れる。

## 7. コミットメッセージ

- 1行目は英語の命令形で、何を変えたかを書く（例: `Add LRU prefetch for adjacent frames`）。
- 本文には「なぜ」と、計測値・トレードオフ・未対応事項を書く。
- AI が作成したコミットには `Co-Authored-By:` を付け、AI の関与を隠さない。

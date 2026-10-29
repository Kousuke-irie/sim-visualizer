# Sim Visualizer

[![CI](https://github.com/Kousuke-irie/sim-visualizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Kousuke-irie/sim-visualizer/actions/workflows/ci.yml)

海洋・生態系結合シミュレーション（Fortran 製）の計算結果を、ブラウザ上で対話的に可視化する Web アプリです。
図を変えるたびに Python スクリプトの定数を書き換えて実行していた作業を、「ブラウザで選ぶだけ」に置き換えることを目的に開発しました。

- **断面ビュー** — Tecplot 形式 `.plt` の任意断面（XY / XZ / YZ）をコンター図＋流速ベクトルで表示
- **時系列ビュー** — 観測地点ごとの `.dat` を深度別の時系列で表示
- **ディレクトリモード** — 計算結果ディレクトリを丸ごと開き、時間スライダーで時間発展を追う
- **比較** — 2つのラン（感度実験など）を同じ時刻・同じ断面で比べる（差 B−A / 並べる / 地点時系列の重ね描き）
- **新しいラン** — 開いたランを元に、`input.dat` の値と `eco.h` の定数を変えた新しいランをブラウザから作る（ホストの runner が作成）

## アーキテクチャ

```
frontend (React + TypeScript + Plotly.js)        backend (FastAPI + NumPy)
  ・描画パラメータの状態管理                ──>    ・.plt / .dat / input.dat のパース
  ・Plotly で contour + 自作 quiver を描画   <──    ・断面抽出、LRU キャッシュ
  ・色・レベル数・ラベル等はブラウザ内で完結   JSON  ・画像は生成せず「生の数値」だけ返す
```

パラメータを「データが変わるもの（断面・変数・時刻）」と「見た目だけ変わるもの（色・等値線・ラベル等）」に分け、
後者はサーバーと通信せずに即座に再描画します。この分離は E2E テストで検証しています
（[`frontend/e2e/section.spec.ts`](frontend/e2e/section.spec.ts)）。

詳細は [DESIGN.md](DESIGN.md) と [DESIGN_directory_mode.md](DESIGN_directory_mode.md) を参照してください。

## 起動

```bash
cp .env.example .env   # DATA_DIR に計算結果ディレクトリの親を指定
docker compose up
```

http://localhost:5173 を開きます。`DATA_DIR` はコンテナ内の `/data` に読み取り専用でマウントされます。
ディレクトリモードで開けるのはこの `/data` 配下だけです（Docker を使わずに起動する場合は、環境変数 `SIMVIZ_DATA_ROOTS` で計算結果の親ディレクトリを指定します）。

## 再計算（runner）

新しいランの作成（と、今後追加する計算の実行）は、Docker ではなく**ホストの Mac で動く runner** が行います。
手作業と同じ gfortran で動かして既存の結果と数値を揃えるためと、Docker からは計算結果を読み取り専用でしか見せないためです
（設計: [DESIGN_research_features.md](DESIGN_research_features.md) §4）。

1. `.env` に `DATA_DIR`（絶対パス）と `SIMVIZ_RUNNER_TOKEN` を書く（`.env.example` 参照）
2. ホストのターミナルで runner を起動する（`127.0.0.1:8100` でだけ待ち受け、トークンの無い要求は拒否します）

```bash
cd backend && set -a && . ../.env && set +a && .venv/bin/python -m app.runner
```

3. `docker compose up` で起動したアプリの「ディレクトリモード → 新しいラン」から使う。runner が起動していなければ、画面に起動方法が表示されます

runner が書き込むのは、元のランと同じ場所に作る**新しいランのディレクトリの中だけ**です。既存のランは読むだけで変更しません。

## 開発・テスト

| 種類 | 対象 | コマンド |
|---|---|---|
| Lint / Format | backend | `ruff check app && ruff format --check app` |
| 単体・API テスト | backend（pytest） | `pytest --cov=app` |
| Lint / Format | frontend（ESLint + Prettier） | `npm run lint && npm run format:check` |
| 型検査 | frontend | `npm run typecheck` |
| 単体テスト | frontend（Vitest） | `npm test` |
| E2E | 実サーバー＋ブラウザ（Playwright） | `npm run e2e` |

```bash
# backend
cd backend
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest

# frontend
cd frontend
npm ci
npm test
npx playwright install chromium
PYTHON=../backend/.venv/bin/python npm run e2e   # backend と Vite を自動起動する
```

API の TypeScript 型は Pydantic モデルから自動生成しています（`backend/scripts/export_openapi.py` → `npm run gen:api`）。
モデルを変えて再生成を忘れると、CI の「API types up to date」ジョブが失敗します。

テスト用データは実データと同じ形式の合成データを [`backend/app/tests/sample_data.py`](backend/app/tests/sample_data.py) で生成します
（研究データそのものはリポジトリに含めていません）。

CI（GitHub Actions）では push / PR ごとに backend・frontend・E2E・Docker ビルドを実行します。

## 技術スタック

FastAPI / NumPy / Pydantic / React 18 / TypeScript / Vite / Plotly.js / Docker Compose / pytest / ruff / Vitest / Playwright / ESLint / Prettier / GitHub Actions

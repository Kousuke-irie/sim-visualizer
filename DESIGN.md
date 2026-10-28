# シミュレーションデータ可視化Webアプリ — 設計書

海洋・生態系シミュレーションの出力を、ブラウザ上でアップロード・可視化・ダウンロードできるローカルWebアプリの要件定義および詳細設計。

---

## 1. 背景・目的

海洋・生態系シミュレーションの出力（Tecplot POINT形式の空間データ、および深度別の時系列データ）を、従来はPythonスクリプト（`plot.py`）で個別に可視化していた。ファイルごとのコード修正、断面位置・属性・軸の変更、ターミナル実行という手間を解消するため、ブラウザ上でファイルをアップロードし、UIでパラメータを調整しながら可視化・ダウンロードできるWebアプリを構築する。

達成したいこと:

- ファイルをローカルからアップロードしてWeb上で可視化する
- 各種パラメータの調整をUI上ででき、すぐにグラフに反映される
- 作成した画像はダウンロード可能

---

## 2. 利用形態・前提

利用者は本人のみ、ローカル環境（`localhost`）で使用する。認証・マルチユーザー・クラウド公開は対象外。ファイルはローカルのバックエンドプロセス内でのみ処理され、外部送信は行わない。

---

## 3. 対応データ形式

### 3.1 断面データ（Tecplot POINT形式 `.plt`）

`TITLE` / `VARIABLES` / `ZONE I=..,J=..,K=..,F=POINT` を含むヘッダの後に、各格子点の全変数値がPOINT順（K→J→I）で並ぶ。変数構成は `X, Y, Z, U, V, W, TEMP, SAL, DIC, TAlk, PHY, ZOO, POC, DOC, DIP, DIN, DOX` 等。ヘッダを自動パースして変数名・格子寸法をコードに埋め込まず取得する。欠損値 `-999.0` はマスク処理する。現状規模は I×J×K = 31×61×21 ≒ 4万点。

### 3.2 時系列データ（`.dat`）

構造は次の通り:

- 1行目: メタ情報（格子位置 `i=`, `j=`, `n=`, 総水深 `h=`）
- 2行目: 列ヘッダ（`time[sec]` と各深度ラベル、例 `-1.75m` … `3.95m`）
- 3行目以降: 各時刻行（1列目=時刻[sec]、2列目以降=各深度での値、指数表記 `0.2000006E+04`）

ファイル名が変数を表す（例 `DIC-01`）。他の変数も同一形式で別ファイルとして与えられる。1画面につき1ファイル（1変数）を表示する。

---

## 4. 画面構成

「断面ビュー」と「時系列ビュー」を用途ごとに最適化した別画面（タブ）として構成する。各画面は、ファイルアップロードとパラメータ操作パネル、描画結果とダウンロードボタンを配置する。

---

## 5. 機能要件

### 5.1 断面ビュー（`.plt`）

`.plt`をアップロードすると、パースした変数名一覧・格子寸法（I×J×K）・各軸の座標範囲がUIに表示される。以下を操作できる。

- **断面方向**: XY・XZ・YZ の3方向を選択。直交軸上の任意の座標値（またはインデックス）で断面位置を指定。指定値に最も近い格子面を自動選択し、実座標値を表示する。
- **描画変数**: 変数一覧から選択。
- **カラーマップ/スケール**: カラーマップを複数候補から選択。塗りコンター・等値線それぞれのレベル数を指定。色範囲（最小・最大）を自動／手動で切替。等値線の表示ON/OFF。
- **流速ベクトル**: 表示ON/OFF、間引き数、スケールをUIで調整。断面方向に応じた2成分を自動選択（YZ→V·W、XZ→U·W、XY→U·V）。
- **軸・レイアウト**: 軸ラベル・タイトルを編集。表示範囲（特に深度 Z）を自動／手動で指定。
- **複数断面**: 断面方向・位置・変数の異なる複数パネルを並べて同時表示（比較用途）。

### 5.2 時系列ビュー（`.dat`）

`.dat`をアップロードすると、メタ情報（格子位置・総水深）と深度ラベル一覧・時刻範囲がUIに表示される。主な見せ方は「深度ごとの時系列折れ線（複数線）」。

- 表示する深度を複数選択（全選択・個別選択）、各線を凡例（深度ラベル）付きで描画。
- 時間軸・値軸の範囲を自動／手動で指定。時間の単位表示（秒／時間）を切替。
- 軸ラベル・タイトルを編集。

### 5.3 共通機能

パラメータ変更はグラフに速やかに反映される。生成した図はPNG（解像度指定可）でダウンロードできる。エラー（ヘッダ不正・寸法不一致・変数欠如・形式不一致）はUIに分かりやすく表示する。

---

## 6. 非機能要件

`.plt`は現状 約4万点規模。アップロードは1回、以降のパラメータ変更による再描画は数百ms〜1秒程度を目標とする。ローカル単独利用のため軽量・単純な構成を優先する。

---

## 7. 技術スタック

> **[フェーズ1実装後に変更]** 当初はMatplotlibでバックエンドがPNGを生成する方式だったが、パラメータ変更のたびにサーバー往復が発生し操作にラグがあったため、**描画をPlotly.jsによるブラウザ側描画に全面移行した**。バックエンドはもはや画像を一切生成せず、パース済みの生データ（座標配列・値の2次元配列）をJSONで返すだけになっている。詳細は「7-1. 描画アーキテクチャ（現行）」を参照。

| 層 | 技術 | 役割 |
|----|------|------|
| バックエンド | FastAPI (Python 3.12) | `.plt`/`.dat` パース、断面・時系列の**データ抽出**（描画はしない）、API提供 |
| フロントエンド | React + TypeScript (Vite) | アップロードUI、パラメータ操作、**Plotly.jsによる描画**、ダウンロード、タブ切替 |
| 描画エンジン | **Plotly.js**（`plotly.js-dist-min` + `@types/plotly.js`） | ブラウザ側でcontour+自作quiver（矢印）を描画。ズーム/パン/PNGダウンロードもPlotly純正機能を利用 |
| 実行環境 | Docker Compose | backend + frontend を一括起動 |

`matplotlib` はbackendから完全に削除済み（`requirements.txt`に存在しない）。日本語フォントのapt install（`fonts-ipafont-gothic`）も、描画がブラウザ側になったため不要になり削除済み。

### 7-1. 描画アーキテクチャ（現行）— ラグ解消の核心

**「データ取得」と「見た目のスタイル」を明確に分離**している点が最重要の設計方針。

- **サーバー往復が必要なもの**（＝データそのものが変わる）: `file_id` / `plane`（断面方向） / `slice_index`（断面位置） / `variable`（描画変数）。これらが変わったときだけ `POST /api/section/data` を呼び、生の格子データを取得する。150msデバウンス（`useDebounced`）してから叩く。
- **サーバー往復が不要なもの**（＝見た目だけが変わる、フロントで完結）: カラーマップ（プリセット/カスタム）、塗りコンター・等値線のレベル数、色範囲、ベクトルの表示/間引き/スケール/太さ/大きさ、軸ラベル・タイトル・単位、縦横比、ダウンロード解像度倍率。これらは全てPlotlyの`layout`/`data`を再計算してクライアント側で再描画するだけで、ネットワークリクエストは一切発生しない。

この分離により「スライダーを動かした瞬間にヌルヌル追従」を実現している。フェーズ2（複数断面）を実装する際も、**この分離を崩さないこと**（＝各パネルのスタイル変更でAPIを叩かない）が重要。

---

## 8. 全体アーキテクチャ

ローカルで2プロセスを起動する。FastAPI（バックエンド、`:8000`）がファイルのパース・抽出を担い、React（フロントエンド、`:5173`）がUIと**描画そのもの**を担う。

```
┌─────────────────────────┐         ┌──────────────────────┐
│  React (Vite)           │  HTTP   │   FastAPI (uvicorn)   │
│  :5173                  │ ──────> │   :8000               │
│                         │         │                       │
│  - Upload UI            │  upload │  - parse .plt/.dat    │
│  - Param panels         │ <────── │  - extract section    │
│  - Plotly.js で描画      │  meta   │    (JSON, 画像化しない)│
│  - ズーム/パン/PNG DL    │         │  - in-memory store    │
│    (Plotlyネイティブ)    │  data   │                       │
│                         │ ──────> │                       │
│                         │ <────── │                       │
│                         │  JSON   │                       │
│                         │ (座標配列・値の2次元配列)         │
└─────────────────────────┘         └──────────────────────┘
```

処理フロー:

1. フロントからファイルをアップロード → バックエンドがパースしてメタ情報を返す
2. フロントで断面方向・位置・変数を選択 → `POST /api/section/data` で生データ（JSON）を取得
3. フロントがPlotly.jsでcontour＋自作quiver（矢印）を描画
4. 色・レベル数・ラベル・ベクトル見た目・縦横比などのスタイル変更は、取得済みデータをもとにフロントのみで再描画（サーバー往復なし）

アップロードしたファイルはバックエンド側でセッション単位に保持し、断面方向・位置・変数の変更のたびに再アップロードせず再抽出する。

---

## 9. ディレクトリ構成（現状。太字は当初設計から変わった/追加された点）

```
plotApp/
├── DESIGN.md
├── plot.py                     # 移植元の元スクリプト（参照用、実行はされない）
├── docker-compose.yml          # backend + frontend を一括起動
├── .claude/launch.json         # プレビュー用起動設定（docker-composeのみ）
├── backend/
│   ├── Dockerfile              # python:3.12-slim ベース（**matplotlib/フォント関連は削除済み**）
│   ├── .dockerignore
│   ├── requirements.txt        # fastapi, uvicorn, numpy, python-multipart, pydantic（**matplotlibなし**）
│   └── app/
│       ├── __init__.py
│       ├── main.py             # FastAPI 本体・ルーター登録・CORS
│       ├── config.py           # MISSING_VALUE, SESSION_TTL_SECONDS, CORS_ALLOW_ORIGINS のみ
│       ├── models/
│       │   ├── __init__.py
│       │   ├── section.py      # SectionDataRequest/SectionDataResponse
│       │   ├── timeseries.py   # **フェーズ3で追加：TimeseriesDataResponse**
│       │   └── common.py       # PltMeta, **DatGrid/DatMeta（フェーズ3で追加）**
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── plt_parser.py   # Tecplot POINT形式パーサ
│       │   └── dat_parser.py   # **フェーズ3で追加：時系列(.dat)パーサ**
│       ├── routers/
│       │   ├── __init__.py
│       │   ├── upload.py       # POST /api/upload（.plt/.dat両対応）, GET /api/meta/{id}, DELETE /api/file/{id}
│       │   ├── section.py      # POST /api/section/data
│       │   └── timeseries.py   # **フェーズ3で追加：GET /api/timeseries/data/{file_id}**
│       ├── services/
│       │   ├── __init__.py
│       │   ├── store.py        # アップロード済みデータのインメモリ管理（**PltEntry/DatEntry**）
│       │   └── section_data.py # 断面データ抽出ロジック（描画はしない）
│       └── tests/
│           ├── __init__.py
│           ├── test_plt_parser.py
│           └── test_dat_parser.py  # **フェーズ3で追加**
└── frontend/
    ├── Dockerfile              # node:20-slim ベース（Vite dev server）
    ├── .dockerignore
    ├── package.json            # plotly.js-dist-min, @types/plotly.js
    ├── vite.config.ts          # /api → backend:8000 のプロキシ設定
    ├── tsconfig.json / tsconfig.app.json / tsconfig.node.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx             # ナビバー＋**タブ切替（断面ビュー/時系列ビュー、フェーズ3で追加）**
        ├── index.css           # デザインシステム（CSS変数）・全コンポーネントのスタイル
        ├── constants.ts        # COLOR_PALETTE(15色), COLORMAP_STOPS/GRADIENTS(8プリセット)
        ├── plotly-dist-min.d.ts # plotly.js-dist-min の型宣言（@types/plotly.jsを再エクスポート）
        ├── api/
        │   └── client.ts       # uploadPlt, fetchSectionData, **uploadDat/fetchTimeseriesData（フェーズ3で追加）**
        ├── types/
        │   └── index.ts        # PltMeta, SectionDataRequest/Response, SectionParams, **DatMeta/TimeseriesDataResponse/TimeseriesParams（フェーズ3で追加）**
        ├── components/
        │   ├── common/
        │   │   ├── FileUpload.tsx
        │   │   ├── ErrorBanner.tsx
        │   │   ├── NumberField.tsx
        │   │   ├── RangeField.tsx        # 自動/手動トグル付き min-max（時系列ビューでも再利用）
        │   │   ├── SliderNumberField.tsx # スライダー+数値
        │   │   ├── ColorSwatchPicker.tsx # カスタムカラーマップ用の15色スウォッチ選択
        │   │   ├── ColormapSelect.tsx    # プリセットのグラデーションプレビュー付きドロップダウン
        │   │   ├── PlotlyChart.tsx       # Plotly.jsの薄いReactラッパー（forwardRefでdownloadImage公開）
        │   │   └── icons.tsx             # 共通インラインSVGアイコン群
        │   ├── section/
        │   │   ├── SectionView.tsx       # 断面ビュー全体（アップロード・状態管理・データ取得）
        │   │   ├── SectionControls.tsx   # 方向/位置/変数/カラー/ベクトル/軸/縦横比/解像度
        │   │   └── SectionPlot.tsx       # Plotly描画本体
        │   │       # 複数断面の並べ表示（フェーズ2）は見送り済み（18節参照）
        │   └── timeseries/               # **フェーズ3で追加**
        │       ├── TimeseriesView.tsx    # 時系列ビュー全体（アップロード・meta取得後に全データを一括取得）
        │       ├── TimeseriesControls.tsx # 深度選択（全選択/個別）/時間単位/軸範囲/ラベル/解像度
        │       └── TimeseriesPlot.tsx    # Plotly折れ線（深度ごとに1トレース、COLOR_PALETTEで色分け）
        └── hooks/
            ├── useDebounced.ts
            └── useRender.ts    # useSectionData（データ取得のみ担当。スタイル変更では発火しない）
```

---

## 10. データモデル

### 10.1 アップロード時に返すメタ情報

`.plt` の場合:

```
PltMeta {
  file_id: str                 # セッションID（以降の描画で参照）
  kind: "plt"
  variables: [str]             # ["X","Y","Z","U",...,"DOX"]
  dims: { I: int, J: int, K: int }
  coords: {
    X: [float],                # I方向の一意なX座標（昇順）
    Y: [float],                # J方向
    Z: [float]                 # K方向
  }
  value_ranges: { TEMP: [min,max], SAL: [min,max], ... }  # 欠損除外後
}
```

`.dat` の場合:

```
DatMeta {
  file_id: str
  kind: "dat"
  variable: str                # ファイル名由来（"DIC-01"）
  grid: { i: int, j: int, n: int, h: float }
  depths: [str]                # ["-1.75m","-0.75m",...,"3.95m"]
  depth_values: [float]        # [-1.75,-0.75,...]
  time_range: [float, float]   # [300.0, 11400.8]
  n_times: int
}
```

### 10.2 断面データリクエスト（現行。旧SectionRenderRequestは廃止）

> Matplotlib時代は色・レベル数・ラベル等の**スタイル情報も含めてバックエンドに送り、PNGを生成**させていた。現在はスタイルに関する情報は一切バックエンドに送らず、**「どの断面のデータが欲しいか」だけ**を送る。

```
SectionDataRequest {
  file_id: str
  plane: "XY" | "XZ" | "YZ"    # 断面方向
  slice_index: int             # 直交軸上のインデックス
  variable: str                # 描画変数
  include_vectors: bool        # 流速ベクトル成分(vec_h/vec_v)も含めるか
}
```

### 10.3 断面データレスポンス（現行）

生の格子データをJSONで返す。矩形格子（Xは I のみ、Yは J のみ、Zは K のみに依存）であることを前提に、`values` は必ず `(v方向, h方向)` の2次元配列になるよう揃えてある。欠損値は `null`。

```
SectionDataResponse {
  h_coords: [float]                        # 横軸の座標（例: YZ断面ならY）
  v_coords: [float]                        # 縦軸の座標（例: YZ断面ならZ）
  h_label: str                             # "X" | "Y" | "Z"
  v_label: str
  values: [[float | null]]                 # shape: (len(v_coords), len(h_coords))
  vector_h: [[float | null]] | null        # 流速ベクトルの横成分（例: YZ断面ならV）
  vector_v: [[float | null]] | null        # 流速ベクトルの縦成分（例: YZ断面ならW）
  vector_h_label: str | null
  vector_v_label: str | null
  actual_coord: float                      # 選択された断面の実座標値
  actual_index: int
  value_range: [float, float]              # 欠損除外後の値の最小・最大（自動色範囲のデフォルトに使う）
}
```

### 10.4 描画スタイル（`SectionParams`。フロントの状態のみ、バックエンドには送らない）

`frontend/src/types/index.ts` で定義。カラーマップ・レベル数・ベクトルの見た目・軸ラベル・縦横比・ダウンロード解像度倍率などを保持し、`SectionPlot.tsx` がこれと `SectionDataResponse` からPlotlyの `data`/`layout` を都度構築する。主なフィールド:

```
SectionParams {
  plane, sliceIndex, variable            # ※これらの変更だけがデータ再取得を伴う
  colormap: str                          # プリセット名
  customColormap: { enabled, low, useMid, mid, high }  # カスタムカラー（2〜3色グラデーション）
  fillLevels, lineLevels, showContourLines
  colorRange: { auto, vmin?, vmax? }
  vectors: { show, skip, scale?, width, headWidth }    # width/headWidthはpx単位（matplotlibの値とは無関係の独自スケール）
  axis: {
    title?, xlabel?, ylabel?, unit?      # unit はカラーバーラベルに [単位] として付与
    zlim: { auto, min?, max? }
    aspect: { auto, ratio? }             # ratio = 表示したい「高さ/幅」
  }
  exportScale: number                    # PNGダウンロード時の解像度倍率（Plotlyのscaleパラメータ）
}
```

### 10.5 時系列データレスポンス（現行。フェーズ3で実装。断面ビューと同様、描画はしない）

> 断面ビューと異なり「どの深度を見せるか」はサーバー側の抽出パラメータを必要としない（全深度×全時刻のデータ量が小さいため）。そのため `file_id` だけで全データを一括取得し、深度選択・時間軸単位切替・範囲指定はすべてフロント側で完結させる（サーバー往復なし）。当初の設計時点で想定していた `TimeseriesRenderRequest`（Matplotlib時代の画像生成前提）は採用せず、断面ビューの `SectionDataResponse` と同じ「生データをJSONで返す」方針に統一した。

```
TimeseriesDataResponse {
  times: [float]                # 秒。DatMeta.time_range/n_times と対応する全時刻
  values: [[float]]             # shape: (n_times, n_depths)。列の並びは DatMeta.depths と対応
}
```

### 10.6 時系列描画スタイル（`TimeseriesParams`。フロントの状態のみ、バックエンドには送らない）

`frontend/src/types/index.ts` で定義。`TimeseriesPlot.tsx` がこれと `TimeseriesDataResponse` からPlotlyの `data`/`layout` を都度構築する。

```
TimeseriesParams {
  selectedDepths: [str]                  # 表示する深度ラベル（複数選択・全選択/個別選択）
  timeUnit: "sec" | "hour"               # 時間軸の単位（表示直前に times を換算するだけ）
  timeRange: { auto, min?, max? }
  valueRange: { auto, min?, max? }
  axis: { title?, xlabel?, ylabel? }
  exportScale: number                    # PNGダウンロード時の解像度倍率
}
```

---

## 11. APIエンドポイント仕様

```
POST /api/upload
  リクエスト: multipart/form-data (file)
  処理      : 拡張子（.plt / .dat）で対応パーサを判定してパース
              → store に保持し file_id を発行
  レスポンス: PltMeta または DatMeta
  エラー    : 400 (形式不正・拡張子不明・ヘッダ不正・寸法不一致)

POST /api/section/data
  リクエスト: SectionDataRequest (JSON)
  処理      : store から grid を取得 → 指定断面を抽出（矩形格子なのでh_coords/v_coordsは1次元）
              → 欠損値はnullに変換してJSON化（描画は一切しない）
  レスポンス: SectionDataResponse
  エラー    : 404 (file_id 不明、または.datのfile_idを指定した場合), 400 (変数欠如・パラメータ不正)

GET /api/timeseries/data/{file_id}
  処理      : store から時系列（全深度・全時刻）を取得しそのままJSON化（描画は一切しない）
  レスポンス: TimeseriesDataResponse
  エラー    : 404 (file_id 不明、または.pltのfile_idを指定した場合)

GET /api/meta/{file_id}
  処理      : 保持済みメタ情報の再取得（リロード対策）
  レスポンス: PltMeta または DatMeta

DELETE /api/file/{file_id}
  処理      : store から破棄（メモリ解放）
```

複数断面の並べ表示（5.1節）は一度実装したがUIが崩れる問題があり見送り済み（18節参照）。将来再検討する場合も、フロント側で複数の独立した `SectionDataRequest` を同じ `file_id` に対して発行する形で実現でき、バックエンドの変更は不要な設計になっている（`section_data.py` はステートレスな抽出関数）。

---

## 12. セッション/データ保持

アップロードしたファイルは、パース済みの NumPy 配列（`.plt` は `(K, J, I, nvar)`、`.dat` は時刻配列＋`(n_times, n_depth)` 行列）としてインメモリの辞書 `store: {file_id: ParsedData}` に保持する。パラメータ変更のたびに再パースせず、抽出と描画のみ行い応答を軽くする。

ローカル単独・短時間利用が前提のため、TTL（例: 最終アクセスから数時間）で自動破棄し、プロセス再起動で消える揮発ストアとする。永続化は行わない。単一ワーカー（uvicorn `--reload`）で動かす前提のため、複数ワーカー間のストア共有問題は起きない。**`--workers` は増やさないこと**を設計上の制約とする。

---

## 13. 描画処理の設計方針（現行：Plotly.js によるブラウザ側描画）

> 当初は既存 `plot.py` のロジック（`contourf` → `colorbar` → `contour` → `quiver` → `quiverkey`）をバックエンドの `section_plot.py`（Matplotlib）に移植する方針だったが、**現在はこの移植先ロジックがフロントエンドの `frontend/src/components/section/SectionPlot.tsx` に丸ごと移っている**。`plot.py` は参照用として残っているのみで、実行はされない。

### 13-1. バックエンド側（`backend/app/services/section_data.py`）

描画は行わず、以下のみを担当:

- 断面方向 XY/XZ/YZ の一般化（`PLANE_CONFIG` テーブルで軸2成分・ベクトル2成分・スライス軸を管理）
- 矩形格子を前提に `np.take` でスライスし、`(v方向, h方向, nvar)` の形になるよう軸を揃える
- 欠損値（`-999.0`近傍）を `None` に変換してJSON化

### 断面方向と成分の対応表（変更なし）

| plane | 横軸(h) | 縦軸(v) | ベクトル成分 | 直交軸（スライス） |
|-------|------|------|--------------|--------------------|
| YZ    | Y    | Z    | V, W         | X (i)              |
| XZ    | X    | Z    | U, W         | Y (j)              |
| XY    | X    | Y    | U, V         | Z (k)              |

### 13-2. フロントエンド側（`SectionPlot.tsx`）— 実際の描画ロジック

- **contour**: Plotlyの `type: "contour"` を2枚重ねる。1枚目は `contours.coloring: "fill"` で塗りつぶし（`fill_levels`個）+ `colorbar`、2枚目は `contours.coloring: "lines"` で等値線（`line_levels`個、`showContourLines`でON/OFF）。`connectgaps: false` で欠損（陸地）部分を白抜きにする。
- **カラースケール**: プリセットは `constants.ts` の `COLORMAP_STOPS`（viridis/plasma/inferno/magma/cividis/coolwarm/jet/RdBu_r の近似色配列）から `[[0,color],[1/n,color],...]` 形式に変換。カスタムは低/中/高の指定色から2〜3点のグラデーションを生成（`LinearSegmentedColormap`相当をPlotlyの線形補間で代用）。
- **流速ベクトル（quiver）**: **Plotly.jsにネイティブのquiverトレースは無い**ため自作。「間引き後の各点で矢柄(shaft)を1本のscatter(mode: 'lines')にnullセパレータで連結」+「矢先(head)をmarker(symbol: 'triangle-up', angle: 度数, size)のscatterで別トレース」の2トレース構成。`vectors.scale`が未指定（自動）なら `0.08 * h方向の実座標レンジ ÷ 最大速度` を長さ係数として使う。矢印の基準凡例（quiverkey相当）は `annotations` の矢印付き注釈で表現。
- **縦横比**: `yaxis.scaleanchor: "x"` + `yaxis.scaleratio` で制御。**注意（実装時にハマった点）**: `scaleratio` は「表示したい縦横比」そのものではなく、x軸に対する「単位あたりピクセル数の倍率」。よって `scaleratio = desiredAspect / rawAspect`（`rawAspect = v方向の実座標レンジ ÷ h方向の実座標レンジ`）という式で変換する必要がある。自動モードでは `rawAspect` を `[1/3, 3]` にクランプした値を `desiredAspect` として使う（深度方向が極端に薄い断面でも潰れて見えなくなるのを防ぐため）。手動モードでは `SectionParams.axis.aspect.ratio`（ユーザーがスライダーで直接指定した「高さ/幅」）をそのまま `desiredAspect` として使う。
- **タイトル・軸ラベル・ベクトル凡例のドラッグ移動**: これらはPlotlyのネイティブ `layout.title`/`xaxis.title` ではなく、すべて `layout.annotations`（`xref/yref: "paper"`）として実装。`config.edits.annotationPosition = true` によりブラウザ上でドラッグ移動できる。カラーバーのラベルはPlotly純正のcolorbar titleを使い、`config.edits.colorbarPosition = true` でドラッグ可能にしている。
- **ドラッグ位置・ズーム状態の保持**: `layout.uirevision` を「データセットを一意に表す文字列（file_id+plane+slice+variable）＋リセットカウンタ」にして渡す。これによりPlotlyは、スタイルだけの再描画（`Plotly.react`呼び出し）ではズーム位置やドラッグしたラベル位置を保持し、新しい断面データが来たとき（＝uirevisionが変わったとき）だけ初期位置にリセットする。「ラベル位置をリセット」ボタンはこのリセットカウンタをインクリメントするだけの実装。
- **ズーム/パン/ダウンロード**: Plotly純正のモードバー機能を使用（`scrollZoom: true`）。PNGダウンロードは独自ボタンから `PlotlyChart` コンポーネント（`forwardRef`でDOM要素を公開）経由で `Plotly.downloadImage(el, { format: "png", scale: exportScale })` を呼ぶ。モードバーのデフォルトカメラボタン（`toImage`）は独自ボタンと重複するため非表示にしている。

---

## 14. Docker構成

開発用途のため、ホットリロードが効く**開発モード**を基本とする。ソースコードはボリュームマウントで各コンテナに渡し、編集が即反映されるようにする。バックエンドは `uvicorn --reload`、フロントは Vite dev server をコンテナ内で起動する。

`docker-compose.yml`（イメージ）:

```yaml
services:
  backend:
    build: ./backend
    ports: ["8000:8000"]
    volumes:
      - ./backend:/app
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    ports: ["5173:5173"]
    volumes:
      - ./frontend:/app
      - /app/node_modules        # node_modules はコンテナ側を優先
    command: npm run dev -- --host 0.0.0.0
    depends_on: [backend]
```

フロントの `vite.config.ts` で `/api` へのリクエストを `http://backend:8000` に転送するプロキシを設定する。これにより、ブラウザからは同一オリジン（`localhost:5173`）へのアクセスに見え、CORS設定が実質不要になる。バックエンドのCORSミドルウェアは開発時の保険として `localhost` を許可する程度に留める。

インメモリ `store` はバックエンドコンテナのプロセス内メモリに載る。コンテナが動いている間は保持され、`docker compose down` や再起動で消える揮発性は要件と一致する。

---

## 15. 起動フロー

環境構築は Docker のみ。Python も Node もホストに入れる必要はない。

```
git clone ... && cd sim-visualizer
docker compose up --build      # 初回。以降は docker compose up
# ブラウザで http://localhost:5173 を開く
```

---

## 16. 開発フェーズ

1. **フェーズ1**: 断面ビュー（`.plt`、単一断面）。✅ **完了**。当初はMatplotlibでの実装だったが、その後Plotly.jsによるブラウザ側描画に全面移行し、縦横比手動調整・カスタムカラーマップ・ベクトル太さ調整・プレビューのズームパン・カラーバー単位・ラベルのドラッグ移動なども追加済み（詳細は17節）。
2. **フェーズ2**: 複数断面の並べ表示。**見送り**。UIが崩れる問題があり実装を取り消した（詳細は18節）。優先度を下げ、フェーズ3を先に進めた。
3. **フェーズ3**: 時系列ビュー（`.dat`、深度別折れ線）。✅ **完了**。断面ビューと同様「サーバーは生データを返すだけ、描画・スタイル変更はフロント完結」の方針で実装（詳細は19節）。

各フェーズの終わりに `docker compose up` で起動確認し、次に進む。

---

## 17. フェーズ2着手時の引き継ぎ事項（当時の記録。フェーズ2は見送り・取り消し済み。現状は18節を参照）

### 17-1. 今どうなっているか（要約）

- 断面ビューは**単一断面のみ**表示できる状態。`SectionView.tsx` が1つの `params`（`SectionParams`）状態と1つの `SectionPlot` を持つ構成。
- 描画はすべてPlotly.js（ブラウザ側）。バックエンドは `/api/section/data` でJSONを返すだけ（画像化しない）。7-1節・13節を参照。
- `.env`やビルド成果物以外は現在のディレクトリ構成（9節）が実体と一致している。テストは `backend/app/tests/test_plt_parser.py` のみ（パーサの単体テスト）。

### 17-2. フェーズ2実装の進め方（推奨）

DESIGN.md 5.1節に「複数断面: 断面方向・位置・変数の異なる複数パネルを並べて同時表示（比較用途）」とある通り、以下の形が自然:

1. `SectionView.tsx` の状態を「単一の `params`」から「`SectionPanel[]`（各パネルが独立した `SectionParams` + 独立した `useSectionData` 呼び出しを持つ）」に変更する。
2. 新規 `frontend/src/components/section/SectionPanel.tsx` を作成し、`SectionControls` + `SectionPlot` を1組にまとめる（ディレクトリ構成9節で当初から予定されていたファイル名）。パネルごとに折りたたみ可能にするなど、UIが横に並んだときに破綻しないよう配慮する。
3. パネルの追加・削除UI（例: 「＋断面を追加」ボタン、各パネルに「×削除」ボタン）を `SectionView.tsx` に追加。
4. レイアウトはCSS Grid等でパネルを並べる（`.section-view__body` は現在1サイドバー+1プレビューのgrid固定なので、パネル数に応じた可変グリッドに変更が必要）。
5. **重要**: 各パネルの見た目のスタイル変更（色・レベル数等）は引き続き**そのパネル内で完結**させ、他パネルの再描画やAPI呼び出しを誘発しないこと（7-1節の分離方針を維持）。
6. `file_id` は全パネル共通（同じアップロード済みファイルを参照）でよい。パネルごとに別ファイルをアップロードさせるかどうかは要件次第（DESIGN.mdの想定は同一ファイル内の異なる断面の比較）。
7. バックエンドの変更は基本的に不要（11節末尾を参照）。

### 17-3. 実装上の注意点・ハマりどころ

- **Plotlyの `scaleratio`** は「表示したい縦横比」そのものではない。`scaleratio = desiredAspect / rawAspect` で変換すること（13-2節に詳細。一度符号を逆に実装してバグを埋め込んだ実績あり）。
- ベクトル（矢印）はPlotlyにネイティブのquiverが無いため自作（shaft用scatter + head用scatterの2トレース）。複数パネルにする際も1パネル＝1組のこの2トレースが必要。
- `layout.uirevision` はズーム位置・ドラッグしたラベル位置をパネル単位で保持するための鍵。パネルを増やす際は、パネルごとに一意な `datasetKey`（file_id+plane+slice+variable+パネルID）を渡すこと。
- カラーマップのプリセット色配列・15色パレットは `frontend/src/constants.ts` に集約されている（`COLOR_PALETTE`, `COLORMAP_STOPS`, `COLORMAP_GRADIENTS`）。複数パネルでも共通で使い回せる。

### 17-4. この開発環境固有の制約（引き継ぎ時に念のため）

- このセッションでは **Chrome拡張機能（claude-in-chrome）が接続できず**、ブラウザでの実機確認が直接できなかった。代替手段として、`.claude/launch.json` に一時的な `frontend-local-preview` 設定（`sh -c "cd <絶対パス>/frontend && npm run dev -- --port 5174"`、`vite.config.ts`のプロキシ先を一時的に `http://localhost:8000` に変更）を追加し、`preview_start`/`preview_eval`（`DataTransfer`で疑似ファイルをinput要素に注入）で検証した。検証後は両方の設定を必ず元（`http://backend:8000`、docker-composeのみ）に戻すこと。次のチャットでも同じ制約が起きた場合は、この手順を再利用できる。
- Docker環境は `./frontend:/app` / `./backend:/app` をボリュームマウントしているため、ホスト側でソースを編集すればコンテナ内のVite/uvicornが自動リロードする。フェーズ2でも基本的に `docker compose up --build` の再ビルドは（依存パッケージを追加しない限り）不要。

---

## 18. フェーズ2の取り消し、およびフェーズ3着手時点の記録（同一セッション内でフェーズ3も完了。現状は19節を参照）

### 18-1. フェーズ2を取り消した経緯

17節の方針に沿って複数断面の並べ表示を実装した（`SectionView.tsx` を `panels[]` 配列ベースに変更、新規 `SectionPanel.tsx` を追加、CSSに `.section-panels` グリッドを追加）。しかし実機で確認したところ**UIのレイアウトが崩れる問題があり**、ユーザー判断でフェーズ2自体を見送ることになった。該当実装（`SectionPanel.tsx` の削除、`SectionView.tsx`・`index.css`・`icons.tsx` をフェーズ1完了時点の内容に戻す）はすべて取り消し済み。**現状はフェーズ1完了時点と完全に同じ状態**（単一断面のみ表示、`SectionView.tsx` が1つの `params` を持つ構成）。

- 崩れの具体的な原因（どのブレークポイント・要素で崩れたか）は切り分けられていない。複数断面表示を再度検討する場合は、まずどう崩れたか（スクリーンショット等）を確認してから設計し直すこと。
- 実装時にHMR絡みのID重複バグ（モジュールレベルの可変カウンタでパネルIDを発行すると `Warning: Encountered two children with the same key` が発生）や、この開発環境で `preview_click`/`element.click()` がReactのイベントデリゲーションに載らないことがある、という2点が判明した。次に複数パネルUIに再挑戦する際は、パネルIDは `crypto.randomUUID()` などモジュール外部の可変状態に依存しない方法で発行し、クリック操作の検証で反応がないように見えたら `element[Object.keys(element).find(k=>k.startsWith('__reactProps$'))].onClick(...)` を `preview_eval` 経由で直接呼んで切り分けるとよい。

### 18-2. 今どうなっているか（フェーズ3着手時点）

- 断面ビューは**単一断面のみ**表示できる状態（フェーズ1の状態のまま）。`SectionView.tsx` が1つの `params`（`SectionParams`）状態と1つの `SectionPlot` を持つ構成。17-1節の記述がそのまま現状に一致する。
- 描画はすべてPlotly.js（ブラウザ側）。バックエンドは `/api/section/data` でJSONを返すだけ（画像化しない）。7-1節・13節を参照。
- ディレクトリ構成（9節）が実体と一致している。テストは `backend/app/tests/test_plt_parser.py` のみ。
- 複数断面の並べ表示（5.1節記載の要件）は保留中。優先度としてはフェーズ3（時系列ビュー）を先に実装する。

### 18-3. フェーズ3実装の進め方（推奨）

10.5節・11節末尾に設計時点の想定がある。

1. バックエンド: `backend/app/parsers/dat_parser.py` を新規作成し、3.2節の `.dat` 形式（1行目メタ情報 `i=`,`j=`,`n=`,`h=`／2行目列ヘッダ／3行目以降データ）をパースする。`plt_parser.py` と同様、ヘッダを自動パースし変数名・深度ラベルをハードコードしない。
2. `backend/app/routers/upload.py` の `.plt`/`.dat` 判定ロジックに `.dat` の分岐を実装し、`DatMeta`（10.1節）を返すようにする。
3. 断面ビューと同様「データ取得」と「見た目のスタイル」を分離する方針（7-1節）を踏襲するかを検討する。時系列は断面ほどデータ量が大きくない（1変数×深度×時刻の1次元〜2次元データ）ため、初回アップロード時に全データをフロントに渡し切ってしまい、深度選択・時間軸単位切替・範囲指定は全てフロント側で完結させる設計（サーバー往復なし）が有力。11節の `POST /api/timeseries/render` は当初Matplotlib時代の想定なので、断面ビュー同様Plotly化するなら実質不要になる可能性が高い（着手時に再検討し、不要なら設計を更新すること）。
4. フロントエンド: `frontend/src/components/timeseries/` ディレクトリを新設し、`TimeseriesView.tsx`（アップロード・状態管理）、`TimeseriesControls.tsx`（深度選択・軸範囲・単位切替）、`TimeseriesPlot.tsx`（Plotlyの `scatter`/`line` トレースで深度ごとの折れ線を描画）を作る想定。
5. `App.tsx` に「時系列ビュー」タブを追加する（現在は断面ビューのみの単一タブ構成）。
6. 各フェーズの終わりに `docker compose up` で起動確認する（15節）。

### 18-4. 検証方法（このセッション固有の制約）

- このセッションでは Chrome拡張機能（claude-in-chrome）を使わず、`.claude/launch.json` に一時的な `frontend-local-preview` 設定（`sh -c "cd <絶対パス>/frontend && npm run dev -- --port 5174"`、`vite.config.ts` のプロキシ先を一時的に `http://localhost:8000` に変更）を追加し、`preview_start`/`preview_eval`（`DataTransfer` で疑似ファイルをinput要素に注入）で検証した。検証後は両方の設定を必ず元（`http://backend:8000`、docker-composeのみ）に戻すこと。次のチャットでも同じ制約が起きた場合は、この手順を再利用できる。
- 検証用の `.plt`/`.dat` サンプルファイルはリポジトリに保存していない。必要なら小さな合成データ（`.plt` は `VARIABLES=X,Y,Z,U,V,W,TEMP,SAL` 程度、`.dat` は3.2節の形式で数十時刻×数深度程度）をその場で生成すれば十分。

---

## 19. フェーズ3実装内容（完了）

18-3節の推奨手順に沿って、同一セッション内で実装・検証まで完了した。

### 19-1. バックエンド

- `backend/app/parsers/dat_parser.py`（新規）: 3.2節の `.dat` 形式をパースする。1行目から `i=`/`j=`/`n=`/`h=` を正規表現で抽出し、2行目の列ヘッダから深度ラベル（`-1.75m` 等の形式、正規表現でバリデーション）を取得、3行目以降を数値行列としてパースする。ヘッダ不正・深度ラベル形式不正・列数不一致・行数不足はそれぞれ `DatParseError`（→ 400）として検出する。`plt_parser.py` と対になるテスト `backend/app/tests/test_dat_parser.py` を追加（5ケース）。
- `backend/app/models/common.py` に `DatGrid`/`DatMeta` を追加（10.1節のフィールドと一致）。
- `backend/app/models/timeseries.py`（新規）: `TimeseriesDataResponse`（10.5節）。
- `backend/app/services/store.py`: `PltEntry` に加えて `DatEntry` を追加し、`Entry = Union[PltEntry, DatEntry]` として同じ辞書で管理する。`get_entry`（Plt専用）/`get_dat_entry`（Dat専用）はそれぞれ `isinstance` チェックで型を絞り込み、違う種類の `file_id` を渡すと `KeyError`（→ 404）になる（例: `.dat` の `file_id` を `/api/section/data` に渡すと404）。
- `backend/app/routers/upload.py`: 拡張子（`.plt`/`.dat`、大小文字無視）で分岐し、`.dat` の場合はファイル名（拡張子を除いた部分）を `variable` として使う。レスポンスは `Union[PltMeta, DatMeta]`。
- `backend/app/routers/timeseries.py`（新規）: `GET /api/timeseries/data/{file_id}` で全時刻・全深度の生データをJSONで返すのみ（描画はしない）。
- `backend/app/main.py` にルーター登録を追加。

### 19-2. フロントエンド

- `frontend/src/types/index.ts` に `DatGrid`/`DatMeta`/`TimeseriesDataResponse`/`TimeUnit`/`TimeseriesParams`（10.6節）を追加。
- `frontend/src/api/client.ts` に `uploadDat`/`fetchTimeseriesData` を追加（`uploadPlt` と同じ `POST /api/upload` を叩くが、戻り値の型が異なるだけ）。
- `frontend/src/components/timeseries/`（新規ディレクトリ）:
  - `TimeseriesView.tsx`: `.dat` アップロード → `DatMeta` 取得 → 直後に `GET /api/timeseries/data/{file_id}` で全データを一括取得（`useEffect` で `meta` が変わるたびに1回だけ発火。断面ビューのような「パラメータ変更のたびにサーバー往復」は発生しない）。
  - `TimeseriesControls.tsx`: 深度の全選択/個別選択チェックボックス、時間軸単位（秒/時間）の切替、時間軸範囲・値軸範囲（`RangeField` を再利用）、タイトル・軸ラベル、ダウンロード解像度（`SliderNumberField` を再利用）。
  - `TimeseriesPlot.tsx`: 深度ごとに1本の `scatter`（`mode: "lines"`）トレースを生成。色は `constants.ts` の `COLOR_PALETTE`（15色）を `meta.depths` のインデックスで固定的に割り当てる（選択/非選択に関わらず同じ深度は常に同じ色になるようにするため、"選択中の深度だけのインデックス" ではなく "全深度中のインデックス" で色を引く）。`timeUnit` が `hour` のときは表示直前に `times` を3600で割るだけで、データ自体の再取得は発生しない。
- `frontend/src/App.tsx`: 断面ビュー/時系列ビューの切替タブを追加（`.segmented` の見た目を流用）。タブ切替は条件付きレンダリングのため、切り替えるとそれぞれのビューの状態はリセットされる（要件上問題ないため意図的に許容）。
- `frontend/src/index.css`: `.app__tabs { margin-left: auto; }` のみ追加。断面ビューの `.section-view`/`.section-controls`/`.plot-card` 等のレイアウトクラスは時系列ビューでもそのまま再利用（見た目の一貫性のため、命名は "section-" 接頭辞のままだが両ビュー共通のレイアウトユーティリティとして機能している）。

### 19-3. 動作確認

- バックエンド: `docker compose exec backend python -m pytest app/tests -q` で9件（plt 4件 + dat 5件）全て通過。`pytest` は `requirements.txt` に含まれていないため、確認時はコンテナ内に一時インストールした（`requirements.txt` へ恒久追加はしていない。次回同様の確認をする場合は同じ手順で一時インストールすればよい）。
- `curl` で `/api/upload`（.dat）→ `DatMeta` 取得、`/api/timeseries/data/{file_id}` → `TimeseriesDataResponse` 取得、`/api/section/data` に .dat の `file_id` を渡すと404になることを確認済み。
- フロントエンド: 18-4節と同じ手順（`frontend-local-preview` + `DataTransfer` 注入）で、タブ切替・`.dat` アップロード・深度チェックボックスのON/OFF・秒/時間の単位切替・エラー表示（不正な `.dat` ファイル）を実機確認済み。検証後は `vite.config.ts`/`.claude/launch.json` を元に戻し、スクラッチ領域の一時ファイルも削除済み。
- このセッションでも `preview_click` がReactのイベントデリゲーションに載らない現象が再発したため、18-1節に記載した「Fiber経由で `onClick`/`onChange` を直接呼ぶ」手法で切り分けて検証した。次回も同様の現象が起きたら同じ手法を使うこと。

### 19-4. 今後の拡張候補（未着手）

- 複数断面の並べ表示（フェーズ2、5.1節）は見送ったまま。再挑戦する場合は18-1節の教訓（HMRでのID重複、`preview_click` の挙動）を踏まえること。
- 時系列ビューも複数ファイル（複数変数）を並べて比較したい場合、断面ビューのフェーズ2と同様の構成変更が考えられるが、現時点では要望なし。

## 20. フロントエンドの構成整理（2026-10、リファクタ計画 PR6）

19節で「タブ切替は条件付きレンダリングのため状態がリセットされる（意図的に許容）」としていたが、
ディレクトリモードの追加後は「断面ビューで1枚確認 → ディレクトリモードで時間発展を見る → 戻る」という往復が増え、
そのたびにアップロードやディレクトリのオープンをやり直す負担が大きくなったため、方針を変更する。

- **タブを切り替えても状態を保持する。** `App.tsx` は3つのビューを常にマウントし、非表示のビューは `hidden` で隠す。
  ディレクトリモード内の「空間分布 / 時系列」サブタブも同様。非表示中の Plotly の図は、再表示時に
  `PlotlyChart` の `ResizeObserver` が大きさを合わせ直す。
  - トレードオフ: 開いたビューの図とデータがすべてメモリに残る。対象データ（1断面あたり数十KB）では問題にならない。
- **データ取得は `hooks/useLatestRequest.ts` に一本化する。** 「リクエストの内容（JSON）が変わったときだけ取得し、
  遅れて返った古い応答は捨て、失敗しても直前のデータは表示し続ける」。見た目のパラメータはリクエストに含めないので、
  13節の「見た目の変更では通信しない」方針はこのフックの性質として保証される（E2E でも検証）。
- **ディレクトリモードは `DirectorySectionPanel` / `DirectoryTimeseriesPanel` に分割する。** 各パネルが自分の状態を持ち、
  `key={dir_id}` によって別のディレクトリを開くと初期状態から始まる（以前は親が12個の状態を手作業でリセットしていた）。
- **描画の組み立ては純粋関数に寄せる。** `sectionFigure.ts` に加え `timeseriesFigure.ts` を設け、既定値は
  `sectionDefaults.ts` / `timeseriesParams.ts` に集約して、断面ビューとディレクトリモードで定義を書き写さない。

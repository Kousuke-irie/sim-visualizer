# シミュレーションデータ可視化Webアプリ — 追加設計書：ディレクトリ読み込みモード

`DESIGN.md`（単一ファイルのアップロード方式）を拡張し、シミュレーション出力ディレクトリ全体（`mecamamo/` のような大元ディレクトリ）を指定すると、`.plt`（空間分布・時間軸付き）と hist の `.dat`（地点×パラメータの時系列）を自動発見して可視化できるようにする。本書は `input.dat` と `mecnest.f90` の実コードで検証した仕様に基づく。

---

## 1. 対象ディレクトリ構成

```
mecamamo/                      # 大元ディレクトリ（名前は任意）
├── input.dat                  # 諸設定（計算期間・plt間隔・hist地点位置など）
├── field2/                    # 連番 .plt（空間分布）: tec-00001.plt, tec-00002.plt, ...
├── hist/                      # 時系列 .dat: DIC-01.dat, TAlk-04.dat, ...
├── field1/                    # (result1) 補助出力。本アプリでは未使用でよい
├── data/ wind/ river/ clim/ obc/   # 入力データ。可視化対象外
└── restart.bin                # リスタート。対象外
```

サブディレクトリ名（`hist`, `field1`, `field2`）は固定ではなく `input.dat` の末尾3行から取得する（後述）。`mecamamo` という名前にも依存しない。

---

## 2. データの与え方：ボリュームマウント

`.plt` は1ファイル約10MBで多数あるため、ブラウザからのアップロードは非現実的。**大元ディレクトリをバックエンドコンテナにボリュームマウントし、バックエンドがサーバー側で直接読む**方式とする。

```yaml
# docker-compose.yml（抜粋・追加）
services:
  backend:
    volumes:
      - ./backend:/app
      - ${DATA_DIR:-./data}:/data:ro     # 大元ディレクトリを /data として読み取り専用マウント
```

起動時に `DATA_DIR` 環境変数で大元ディレクトリを指定する（例: `DATA_DIR=/path/to/mecamamo docker compose up`）。UIからは「マウント済み `/data` 配下のディレクトリを選択」または「パスを入力」する。読み取り専用（`:ro`）とし、アプリが元データを書き換えないことを保証する。

### 2.1 アクセスできるパスの制限（データルート）

当初はローカル単独利用を前提に、`/api/directory/browse` と `/api/directory/open` がサーバー上の任意のパスを受け付けていた。
しかし調査の結果、`input.dat` に書かれた出力ディレクトリ名（`../outside/field2` や絶対パス）を経由すると、
計算結果ディレクトリの外のファイルまで読めてしまうことが分かった（パス・トラバーサル）。
ポートが LAN に見えている環境では、第三者がファイルシステムの構造を探れることにもなる。

そこで、アクセスを許可する**データルート**を設け、次の3つすべてをその配下に制限する。

| 入口 | 判定に使うパス | 配下でないとき |
|---|---|---|
| `GET /api/directory/browse` | クエリの `path`（省略時は最初のデータルート） | 403 |
| `POST /api/directory/open` | リクエストの `path` | 403 |
| `input.dat` の出力先（hist / field2） | 計算結果ディレクトリと連結したパス | 400（`input.dat` の内容の問題として扱う） |

- データルートは環境変数 `SIMVIZ_DATA_ROOTS`（`os.pathsep` 区切りで複数可）で指定し、既定は `/data`（docker compose のマウント先）。
  Docker を使わずに起動する場合は、計算結果の親ディレクトリを明示的に指定する。以前はホームディレクトリを既定にしていたが、
  「指定しなければ何も読めない」ほうを安全側として選んだ。
- 判定は `realpath` でシンボリックリンクと `..` を解決したうえで、`commonpath` によりパス要素単位で行う。
  文字列の前方一致だと `/data` が `/data2` を許してしまうため。
- `input.dat` の出力先に `../` が使われているかは実データで確認できていないため、**データルート配下に収まる限りは許可する**。
  計算結果ディレクトリの直下に限定するのが最も厳しい案だったが、正しいデータを誤って拒否するリスクを避けた。
- 参照ダイアログはデータルートより上に「上へ」で戻れない。データルート外を指すシンボリックリンクは一覧に出さない。
- 実装は `backend/app/services/path_policy.py`。

---

## 3. input.dat 仕様（mecnest.f90 で検証済み）

`input.dat` は固定順の行構成で、`mecnest.f90`（`open(10,file='input.dat')` 以降の `read(10,*)` 順）と1対1対応する。本アプリが使う行は以下。**行番号はサンプルに準拠。コメント（`#...`）は無視する。**

| 行 | 例 | 変数（f90） | 本アプリでの用途 |
|----|-----|-------------|------------------|
| 1  | `1 5 0 1 1 0` | `isw(1..6)` | `isw(5)`=生態系スイッチ。plt変数構成の予測に補助的に使用（確定はpltヘッダ） |
| 2  | `30 60 21 1` | `in, jn, kn, nest` | 参考情報。実寸法はpltヘッダを優先 |
| 4  | `0.8` | `dt` | 時間刻み[秒] |
| 5  | `86400. 1 0` | `endtime, ntime, irst` | 計算終了時刻[秒] |
| 8  | `3600. 0. 999999999999.` | `fifit2,5,6` | **先頭=`fifit2` → `ifit2=int(fifit2)`。plt出力間隔[秒]** |
| 9  | `10.0` | `dx` | 水平格子間隔[m] |
| 10 | `-2.0 -1.5 ... 4.0` | `z(k)` | Z層の座標配列 |
| 21 | `6 300.0` | `nhist, histout` | hist地点数、hist出力間隔[秒] |
| 22 | `15 30 1 15 10 1 ...` | `ijhist0(1..3, 1..nhist)` | 各hist地点の (i, j, n)。3値×nhist個 |
| 末尾3行 | `hist` / `field1` / `field2` | `result3, result1, result2` | 出力ディレクトリ名。**hist=result3, field2=result2** |

補足:

- 行8の3番目以降やコメントは無視。トークン分割して先頭の数値を `fifit2` とする。
- 行22は `nhist`（行21の先頭）個ぶんの `(i, j, n)` を平坦に並べたもの。`3 × nhist` 個の整数を読む。
- 末尾3行の順序は `result3`（hist）→ `result1`（field1）→ `result2`（field2）。f90 の読み込み順（`read(10,'(a)') result3; result1; result2`）に一致。

### 3.1 パーサ方針

行の絶対位置に依存すると壊れやすいため、**コメント除去 → 空行除去 → トークン列として順に消費**する堅牢な実装とする。各 `read(10,*)` に相当する消費を順に行い、必要な行だけ取り出す。将来モデルが変わっても、消費順を f90 に合わせて調整すれば追従できる。

---

## 4. .plt（field2）の命名・時刻対応（検証済み）

`tecplot2`（mecnest.f90）でのファイル名生成:

```fortran
nt2 = int(time(n)) / abs(ifit2)
write(cnu,'(i5.5)') nt2                 ! 5桁ゼロ埋め
ftec2 = trim(result2)//'/tec-'//cnu//'.plt'
```

したがって:

- ファイル名は **`tec-NNNNN.plt`（5桁ゼロ埋め連番）**。
- 連番 `NNNNN` と時刻の対応は **`時刻[秒] = NNNNN × ifit2`**。例: `ifit2=3600` のとき `tec-00001.plt`→3600秒、`tec-00024.plt`→86400秒。

### 4.1 時間軸の権威：実ファイル優先（確定方針）

`field2/` に歯抜け（一部連番のみ存在）や `input.dat` とのズレがあり得るため、**実在する `.plt` を走査し、その連番から `× ifit2` で時刻ラベルを付ける**。`input.dat` は `ifit2`（間隔）と地点情報の取得に用い、時間スライダーの目盛りは実ファイル集合にスナップさせる。存在しない連番は選べない。

### 4.2 .plt の変数構成はヘッダ依存

`tecplot2` は `isw(5)` と `Np` で VARIABLES 行を分岐する（例: `X,Y,Z,U,V,W,TEMP,SAL,DIC,TAlk,PHY,ZOO,POC,DOC,DIP,DIN,DOX`）。**変数構成は固定せず、各 `.plt` の `VARIABLES` 行を自動パースして取得する**（`DESIGN.md` の方針を踏襲）。格子寸法も `ZONE I=..,J=..,K=..` から取る。`input.dat` 行2の寸法は袖領域の有無でZONEと一致しないため、寸法はヘッダを正とする。

---

## 5. hist（.dat）の命名・構造（検証済み）

`hist0`（mecnest.f90）で、地点番号 `l`（1..nhist）に対し `char(l+48)`（`'1'`..）を用いて生成:

```
tmp-0L.dat  sal-0L.dat  DIC-0L.dat  TAlk-0L.dat
phy1-0L.dat zoo-0L.dat  poc-0L.dat  doc-0L.dat
dip-0L.dat  din-0L.dat  do-0L.dat        （L = 地点番号）
```

- 規則: **`<param>-0<point>.dat`**。例: `DIC-01.dat` = パラメータ `DIC` × 地点 `01`。
- 地点番号は `char(l+48)` により基本1桁（`-01`..`-09`）。**nhist ≤ 9 前提**（10地点以上は命名が崩れる実装）。今回は6地点。
- ファイル名の正規表現（桁数は柔軟に）:
  ```
  ^(?P<param>[A-Za-z0-9]+)-0*(?P<point>\d+)\.dat$
  ```

### 5.1 .dat ヘッダ・本体（実ファイルで確認）

```
1行目: i= 15 j= 30 n=  1  h=   4.0[m]        # 格子位置(i,j,n)と総水深h
2行目: time[sec]   -1.75m  -0.75m  ...  3.95m # 時刻列と各深度ラベル
3行目〜: 300.0  <各深度の値(指数表記 e形式)> ...  # 各時刻行
```

- 1行目から `(i, j, n, h)` を抽出。地点プルダウンの座標表示に使う。
- 2行目から深度ラベル列を抽出（`-1.75m` など）。深度選択UIの選択肢になる。
- `input.dat` 行22の `ijhist0` と、`.dat` ヘッダの `i= j=` は一致する（サンプルで確認: 地点01=(15,30)）。整合チェックに利用可能。

---

## 6. ディレクトリスキャン結果（メタモデル）

大元ディレクトリを指定したとき、バックエンドが返すメタ情報。

```
DirectoryMeta {
  root: str                        # 大元ディレクトリの（マウント内）パス
  input: {
    ifit2: float                   # plt出力間隔[秒]
    endtime: float                 # 計算終了時刻[秒]
    dt: float                      # 時間刻み[秒]
    dx: float                      # 水平格子間隔[m]
    z_levels: [float]              # Z層座標
    nhist: int
    histout: float                 # hist出力間隔[秒]
    result_dirs: { hist: str, field1: str, field2: str }
  }
  points: [                        # hist地点（input.dat行22由来）
    { point: "01", i: 15, j: 30, n: 1, x: float?, y: float? }
    ...
  ]
  plt_frames: [                    # field2の実在ファイルを走査
    { file: "tec-00001.plt", index: 1, time_sec: 3600.0 }
    ...
  ]                                # index昇順。歯抜けはそのまま反映
  timeseries: {                    # hist配下の実在ファイルを走査
    params: ["DIC","TAlk","tmp","sal", ...]     # 発見されたパラメータ一覧
    by_param: {
      "DIC": ["01","02", ...],     # そのパラメータが存在する地点
      ...
    }
  }
}
```

---

## 7. API 追加仕様

`DESIGN.md` の単一ファイルAPIに加えて、ディレクトリモード用のエンドポイントを追加する。

```
POST /api/directory/open
  リクエスト: { path: str }              # マウント内の大元ディレクトリパス
  処理      : input.dat をパース → field2/ と hist/ を走査
              → DirectoryMeta を構築し、セッション(dir_id)として保持
  レスポンス: DirectoryMeta { dir_id, ... }
  エラー    : 400 (input.dat 不在/パース失敗), 404 (パス不在)

POST /api/directory/section/render
  リクエスト: {
    dir_id: str,
    frame_index: int,               # plt_frames の index（時間スライダー由来）
    ...SectionRenderRequest と同じ描画パラメータ（plane/variable/colormap 等）
  }
  処理      : index に対応する tec-NNNNN.plt を（キャッシュ経由で）読み
              → 断面抽出 → Matplotlib 描画
  レスポンス: SectionRenderResponse（+ time_sec を同梱）

POST /api/directory/timeseries/render
  リクエスト: {
    dir_id: str,
    param: str,                     # 例 "DIC"
    point: str,                     # 例 "01"
    ...TimeseriesRenderRequest と同じ描画パラメータ（depths/軸 等）
  }
  処理      : hist/<param>-0<point>.dat を読み → 深度別折れ線を描画
  レスポンス: { image, ... }

GET /api/directory/{dir_id}/meta
  処理      : 保持済み DirectoryMeta の再取得（リロード対策）
```

単一ファイルのアップロードAPI（`/api/upload` など）は併存させ、ディレクトリを使わない単発利用も引き続き可能とする。

---

## 8. .plt キャッシュ設計

時間スライダー操作のたびに約10MBの `.plt` を再パースすると重い。以下でパフォーマンスを確保する。

- **LRUキャッシュ**: パース済み `.plt`（`(K,J,I,nvar)` 配列＋変数リスト＋座標）を、`dir_id + frame_index` をキーに保持。容量上限（例: 直近8フレーム、またはメモリ量ベース）を設ける。
- **先読み（任意・後フェーズ）**: 現在フレームの前後を裏で非同期パースし、スライダー移動の体感を改善。
- **抽出と描画の分離**: パースは1回、以降は断面抽出＋描画のみ。パラメータ（カラーマップ・レベル等）変更ではファイルを再読しない。

メモリ量に注意（10MB×フレーム数）。上限到達時は古いフレームから破棄。プロセス終了・`docker compose down` で揮発（永続化しない）。

---

## 9. UI 拡張

`DESIGN.md` のタブ構成（断面ビュー／時系列ビュー）に、ディレクトリモードの操作を重ねる。

### 9.1 起動〜ディレクトリ選択

アプリ起動後、まず「ディレクトリを開く」でマウント内パスを指定。成功すると `DirectoryMeta` を受け取り、地点一覧・パラメータ一覧・pltフレーム数・計算期間がヘッダ情報として表示される。

### 9.2 空間分布タブ（時間軸付き断面）

既存の断面コントロール（plane / 位置 / 変数 / カラーマップ / レベル / 色範囲 / ベクトル / 軸）に、**時間スライダーと再生コントロール**を追加する。スライダーは `plt_frames` の実在フレームにスナップし、目盛りに時刻（秒／時刻表示を切替可）を表示。スライダー移動で該当フレームを `directory/section/render` に投げて再描画。再生ボタンで順次フレームを進める。複数断面パネル（`DESIGN.md` フェーズ2）は同一フレーム・同一 `dir_id` に対して並列描画。

### 9.3 時系列タブ（地点×パラメータ）

**パラメータ選択**（`timeseries.params`）と**地点選択**（`points`、座標 `(i,j)` 併記）のプルダウンを追加。両者を選ぶと `hist/<param>-0<point>.dat` を `directory/timeseries/render` に投げ、深度別折れ線を描画。深度選択・軸・時間単位は既存の時系列コントロールを流用。

---

## 10. ディレクトリ構成への追加（バックエンド）

`DESIGN.md` の構成に以下を追加する。

```
backend/app/
├── parsers/
│   ├── input_parser.py     # input.dat パーサ（トークン順消費・コメント除去）
│   └── dir_scanner.py      # field2/hist 走査、命名規則パース、DirectoryMeta 構築
├── services/
│   ├── store.py            # 既存（単一ファイル）
│   └── plt_cache.py        # .plt の LRU キャッシュ（dir_id+frame_index キー）
└── routers/
    └── directory.py        # /api/directory/* エンドポイント
```

フロントには `components/directory/`（`DirectoryOpen.tsx`, `TimeSlider.tsx`, `PointParamSelect.tsx`）を追加し、既存の `section/` `timeseries/` コンポーネントを内側で再利用する。

---

## 11. 実装フェーズ（追加分）

`DESIGN.md` のフェーズ1〜3（単一ファイル）を土台に、ディレクトリモードを積む。

1. **フェーズD1**: `input_parser.py` と `dir_scanner.py`。`/api/directory/open` が `DirectoryMeta` を返すところまで（UIはメタ表示のみ）。実データで走査結果を検証。
2. **フェーズD2**: 空間分布タブに時間スライダーを追加し、`directory/section/render` でフレーム切替描画。`plt_cache.py` を導入。
3. **フェーズD3**: 時系列タブに地点×パラメータ選択を追加し、`directory/timeseries/render` で描画。
4. **フェーズD4（任意）**: 再生アニメーション、先読みプリフェッチ、複数断面の同時フレーム表示。

各フェーズ末に `docker compose up`（`DATA_DIR` 指定）で実ディレクトリに対し動作確認する。

---

## 12. 既知の制約・注意

- hist地点番号は1桁前提（`char(l+48)`）。nhist ≤ 9。10地点以上のモデルは命名規則の再確認が必要。
- `.plt` の変数構成・寸法はヘッダを正とする（`input.dat` 行2は袖の有無で不一致になり得る）。
- `input.dat` の行構成はモデル改変で変わり得る。パーサは f90 の読み込み順に対応させる方針とし、位置ベタ書きを避ける。
- hist ヘッダの `i= j=` と `input.dat` 行22の整合を起動時にチェックし、食い違えば警告表示する。
- 実座標 `x, y` の算出（`dx` と袖オフセット）は、断面ビューで既に `.plt` の X,Y を持つため、地点表示では補助情報に留めてよい。

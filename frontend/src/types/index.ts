// API の入出力型はバックエンドの Pydantic モデルから自動生成した api.gen.ts を正とする（手で書き写さない）。
// 生成: backend で `python scripts/export_openapi.py` → frontend で `npm run gen:api`。CI が生成物の鮮度を検査する。
import type { components } from './api.gen'

type Schemas = components['schemas']

// --- アップロード方式（断面ビュー・時系列ビュー） ---

export type Dims = Schemas['Dims']
export type Coords = Schemas['Coords']
export type PltMeta = Schemas['PltMeta']
export type DatGrid = Schemas['DatGrid']
export type DatMeta = Schemas['DatMeta']
export type UploadedMeta = PltMeta | DatMeta

// サーバーから取得する生の断面データ（描画自体はフロントで行う）
export type SectionDataRequest = Schemas['SectionDataRequest']
export type SectionDataResponse = Schemas['SectionDataResponse']
export type Plane = SectionDataRequest['plane']

// サーバーから取得する生の時系列データ（深度選択・軸範囲・単位切替はフロントのみで完結）。
// values は shape (n_times, n_depths)、depths の並びは DatMeta.depths と対応
export type TimeseriesDataResponse = Schemas['TimeseriesDataResponse']

// --- ディレクトリモード（シミュレーション出力ディレクトリを直接指定） ---

export type ResultDirs = Schemas['ResultDirs']
export type DirectoryInputMeta = Schemas['DirectoryInputMeta']
export type HistPoint = Schemas['HistPoint']
export type PltFrameMeta = Schemas['PltFrameMeta']
export type TimeseriesIndex = Schemas['TimeseriesIndex']
export type DirectoryMeta = Schemas['DirectoryMeta']
export type DirectoryOpenRequest = Schemas['DirectoryOpenRequest']
export type DirectorySectionDataRequest = Schemas['DirectorySectionDataRequest']
export type DirectorySectionDataResponse = Schemas['DirectorySectionDataResponse']
export type DirectoryTimeseriesRequest = Schemas['DirectoryTimeseriesRequest']
export type DirectoryTimeseriesResponse = Schemas['DirectoryTimeseriesResponse']
export type DirectoryBrowseEntry = Schemas['DirectoryBrowseEntry']
export type DirectoryBrowseResponse = Schemas['DirectoryBrowseResponse']

// --- 2ケース比較（DESIGN_research_features.md §3） ---

export type CompareCheckRequest = Schemas['CompareCheckRequest']
export type CompareCheckResponse = Schemas['CompareCheckResponse']
export type ComparePoint = Schemas['ComparePoint']
export type CompareSectionRequest = Schemas['CompareSectionRequest']
export type CompareSectionResponse = Schemas['CompareSectionResponse']
export type CompareTimeseriesRequest = Schemas['CompareTimeseriesRequest']
export type CompareTimeseriesResponse = Schemas['CompareTimeseriesResponse']

// === ここから下はフロントエンドだけが持つ UI 状態（サーバーには送らない）。手書きで管理する ===

// --- 表示スタイル（すべてクライアント側のみで完結し、変更は即座に反映される） ---

export type ColorRange = { auto: boolean; vmin?: number; vmax?: number }

export type CustomColormapState = {
  enabled: boolean
  low: string
  useMid: boolean
  mid: string
  high: string
}

export type VectorConfig = { show: boolean; skip: number; scale?: number; width: number; headWidth: number }
export type ZLim = { auto: boolean; min?: number; max?: number }
export type AspectConfig = { auto: boolean; ratio?: number }
export type AxisConfig = {
  title?: string
  xlabel?: string
  ylabel?: string
  unit?: string
  zlim: ZLim
  aspect: AspectConfig
}

export type SectionParams = {
  plane: Plane
  sliceIndex: number
  variable: string
  colormap: string
  customColormap: CustomColormapState
  fillLevels: number
  lineLevels: number
  showContourLines: boolean
  colorRange: ColorRange
  vectors: VectorConfig
  axis: AxisConfig
  exportScale: number
}

export type LabelPosition = { x: number; y: number }
export type LabelPositions = {
  title: LabelPosition
  xlabel: LabelPosition
  ylabel: LabelPosition
  vectorKey: LabelPosition
}

// --- 時系列ビュー ---

export type TimeUnit = 'sec' | 'hour'

export type TimeseriesParams = {
  selectedDepths: string[]
  timeUnit: TimeUnit
  timeRange: { auto: boolean; min?: number; max?: number }
  valueRange: { auto: boolean; min?: number; max?: number }
  axis: { title?: string; xlabel?: string; ylabel?: string }
  exportScale: number
}

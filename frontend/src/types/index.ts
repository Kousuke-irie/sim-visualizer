export type Dims = { I: number; J: number; K: number }
export type Coords = { X: number[]; Y: number[]; Z: number[] }

export type PltMeta = {
  file_id: string
  kind: 'plt'
  variables: string[]
  dims: Dims
  coords: Coords
  value_ranges: Record<string, [number, number]>
}

export type Plane = 'XY' | 'XZ' | 'YZ'

// --- サーバーから取得する生の断面データ（描画自体はフロントで行う） ---

export type SectionDataRequest = {
  file_id: string
  plane: Plane
  slice_index: number
  variable: string
  include_vectors: boolean
}

export type SectionDataResponse = {
  h_coords: number[]
  v_coords: number[]
  h_label: string
  v_label: string
  values: (number | null)[][]
  vector_h: (number | null)[][] | null
  vector_v: (number | null)[][] | null
  vector_h_label: string | null
  vector_v_label: string | null
  actual_coord: number
  actual_index: number
  value_range: [number, number]
}

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

// --- 時系列ビュー（.dat） ---

export type DatGrid = { i: number; j: number; n: number; h: number }

export type DatMeta = {
  file_id: string
  kind: 'dat'
  variable: string
  grid: DatGrid
  depths: string[]
  depth_values: number[]
  time_range: [number, number]
  n_times: number
}

// サーバーから取得する生の時系列データ（深度選択・軸範囲・単位切替はフロントのみで完結）
export type TimeseriesDataResponse = {
  times: number[]
  values: number[][] // shape (n_times, n_depths)、depths の並びは DatMeta.depths と対応
}

export type TimeUnit = 'sec' | 'hour'

export type TimeseriesParams = {
  selectedDepths: string[]
  timeUnit: TimeUnit
  timeRange: { auto: boolean; min?: number; max?: number }
  valueRange: { auto: boolean; min?: number; max?: number }
  axis: { title?: string; xlabel?: string; ylabel?: string }
  exportScale: number
}

// --- ディレクトリモード（シミュレーション出力ディレクトリを直接指定） ---

export type ResultDirs = { hist: string; field1: string; field2: string }

export type DirectoryInputMeta = {
  ifit2: number
  endtime: number
  dt: number
  dx: number
  z_levels: number[]
  nhist: number
  histout: number
  result_dirs: ResultDirs
}

export type HistPoint = { point: string; i: number; j: number; n: number; x: number | null; y: number | null }

export type PltFrameMeta = { file: string; index: number; time_sec: number }

export type TimeseriesIndex = { params: string[]; by_param: Record<string, string[]> }

export type DirectoryMeta = {
  dir_id: string
  root: string
  input: DirectoryInputMeta
  points: HistPoint[]
  plt_frames: PltFrameMeta[]
  timeseries: TimeseriesIndex
  plt_variables: string[]
  plt_dims: Dims
}

export type DirectorySectionDataRequest = {
  dir_id: string
  frame_index: number
  plane: Plane
  slice_index: number
  variable: string
  include_vectors: boolean
}

export type DirectorySectionDataResponse = SectionDataResponse & {
  frame_index: number
  time_sec: number
}

export type DirectoryTimeseriesRequest = {
  dir_id: string
  param: string
  point: string
}

export type DirectoryTimeseriesResponse = {
  variable: string
  point: string
  grid: DatGrid
  depths: string[]
  depth_values: number[]
  times: number[]
  values: number[][]
}

export type DirectoryBrowseEntry = { name: string; path: string; has_input_dat: boolean }

export type DirectoryBrowseResponse = { path: string; parent: string | null; entries: DirectoryBrowseEntry[] }

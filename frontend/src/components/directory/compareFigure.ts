// 2ケース比較の「差分（B−A）」表示を、既存の断面図（SectionPlot）で描ける形に組み立てる純粋関数。
// 差分そのものはサーバーで計算済み。ここで決めるのは見た目（0 を中心にした対称な色範囲・タイトル）だけ。
import type { Data } from 'plotly.js'
import { LINE_COLORS } from '../../constants'
import type {
  CompareSectionResponse,
  CompareTimeseriesResponse,
  SectionDataResponse,
  SectionParams,
  TimeseriesParams,
} from '../../types'
import { SLICE_COORD_LABEL } from '../section/sectionFigure'

export type RunLabels = { a: string; b: string }

// 計算結果ディレクトリのパスから、画面に出す短い名前（末尾のディレクトリ名）を取る
export function runLabel(root: string): string {
  const parts = root.split('/').filter(Boolean)
  return parts[parts.length - 1] ?? root
}

// 差分の色範囲は 0 を中心に対称にする（赤=B が大きい、青=B が小さい、を一目で読めるように）。
// 差が全く無いときは範囲が潰れるので ±1 にして、全面が中央色で描かれるようにする
export function symmetricRange(range: [number, number] | null): [number, number] {
  if (!range) return [-1, 1]
  const m = Math.max(Math.abs(range[0]), Math.abs(range[1]))
  return m > 0 ? [-m, m] : [-1, 1]
}

export function diffTitle(res: CompareSectionResponse, params: SectionParams, labels: RunLabels): string {
  const coord = `${SLICE_COORD_LABEL[params.plane]} = ${res.a.actual_coord.toFixed(1)} m`
  return `${params.variable} の差（B − A）: ${labels.b} − ${labels.a}（${params.plane}断面, ${coord}）`
}

export function buildDiffView(
  res: CompareSectionResponse,
  params: SectionParams,
  labels: RunLabels,
): { data: SectionDataResponse; params: SectionParams } {
  const data: SectionDataResponse = {
    ...res.b,
    values: res.diff,
    // 値範囲は実際の差分の範囲（画面の「値範囲」表示に使う）。色だけを対称にするのは下の colorRange で行う
    value_range: res.diff_range ?? [0, 0],
    // 流速の差の矢印は読み取りにくいので、差分図には描かない
    vector_h: null,
    vector_v: null,
    vector_h_label: null,
    vector_v_label: null,
  }
  const [vmin, vmax] = symmetricRange(res.diff_range)
  return {
    data,
    params: {
      ...params,
      // 色範囲が「自動」のときだけ 0 中心の対称にする。手動で指定した範囲は尊重する
      colorRange: params.colorRange.auto ? { auto: false, vmin, vmax } : params.colorRange,
      axis: { ...params.axis, title: params.axis.title || diffTitle(res, params, labels) },
    },
  }
}

type SectionView = { data: SectionDataResponse; params: SectionParams }

// 並べた図は幅が半分になるので、タイトルは「どちらのランか」と変数だけにする（断面の位置は2枚で共通なので省く）
function sideTitle(side: 'A' | 'B', label: string, params: SectionParams): string {
  return `${side}: ${label} — ${params.axis.title || params.variable}`
}

// 「並べる」表示。同じ色が同じ値を表すよう、色範囲が「自動」なら A・B の値範囲の和集合を両方に使う
export function buildPairViews(
  res: CompareSectionResponse,
  params: SectionParams,
  labels: RunLabels,
): { a: SectionView; b: SectionView } {
  const colorRange = params.colorRange.auto
    ? {
        auto: false,
        vmin: Math.min(res.a.value_range[0], res.b.value_range[0]),
        vmax: Math.max(res.a.value_range[1], res.b.value_range[1]),
      }
    : params.colorRange
  const view = (side: 'A' | 'B', data: SectionDataResponse, label: string): SectionView => ({
    data,
    params: { ...params, colorRange, axis: { ...params.axis, title: sideTitle(side, label, params) } },
  })
  return { a: view('A', res.a, labels.a), b: view('B', res.b, labels.b) }
}

// 地点時系列の重ね描きで使う深度の一覧。A の並びを基準に、B にしか無い深度を後ろに足す
// （地点の水深が違えば深度ラベルも違うため）
export function unionDepths(res: CompareTimeseriesResponse): string[] {
  return [...res.a.depths, ...res.b.depths.filter((d) => !res.a.depths.includes(d))]
}

// A は実線、B は破線。色は深度ごとに固定し、同じ深度の A と B が同じ色になるようにする
export function buildOverlayTraces(
  res: CompareTimeseriesResponse,
  params: TimeseriesParams,
  labels: RunLabels,
): Data[] {
  const depths = unionDepths(res)
  const unitDivisor = params.timeUnit === 'hour' ? 3600 : 1
  const traces: Data[] = []
  for (const [side, series, label, dash] of [
    ['A', res.a, labels.a, 'solid'],
    ['B', res.b, labels.b, 'dash'],
  ] as const) {
    const times = series.times.map((t) => t / unitDivisor)
    series.depths.forEach((depth, column) => {
      if (!params.selectedDepths.includes(depth)) return
      traces.push({
        type: 'scatter',
        mode: 'lines',
        name: `${side} ${depth}`,
        legendgroup: side,
        x: times,
        y: series.values.map((row) => row[column]),
        line: { color: LINE_COLORS[depths.indexOf(depth) % LINE_COLORS.length], dash },
        hovertemplate: `${side}: ${label}<br>${depth}<br>time: %{x}<br>%{y}<extra></extra>`,
      })
    })
  }
  return traces
}

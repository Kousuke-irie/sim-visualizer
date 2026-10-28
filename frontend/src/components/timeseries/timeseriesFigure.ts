// 時系列グラフの Plotly 図形を組み立てる純粋関数群（sectionFigure.ts と同じ方針）。
// React やネットワークに依存しないため、timeseriesFigure.test.ts で直接検証する。
import type { Data, Layout } from 'plotly.js'
import { COLOR_PALETTE } from '../../constants'
import type { DatMeta, TimeseriesDataResponse, TimeseriesParams } from '../../types'

export type TimeseriesFigureMeta = Pick<DatMeta, 'depths' | 'variable'>

type AxisRange = TimeseriesParams['timeRange']

export function defaultTitle(meta: TimeseriesFigureMeta): string {
  return `${meta.variable} 時系列（深度別）`
}

// 手動指定で min・max の両方が揃っているときだけ範囲を固定し、それ以外は Plotly の自動に任せる
export function resolveRange(range: AxisRange): [number, number] | undefined {
  return !range.auto && range.min != null && range.max != null ? [range.min, range.max] : undefined
}

export function buildTimeseriesTraces(
  meta: TimeseriesFigureMeta,
  data: TimeseriesDataResponse,
  params: TimeseriesParams,
): Data[] {
  const unitDivisor = params.timeUnit === 'hour' ? 3600 : 1
  const times = data.times.map((t) => t / unitDivisor)

  return (
    meta.depths
      .map((depth, depthIndex) => ({ depth, depthIndex }))
      .filter(({ depth }) => params.selectedDepths.includes(depth))
      // 色は「表示中の何本目か」ではなく深度の並び順で決め、深度を絞り込んでも同じ深度は同じ色のままにする
      .map(({ depth, depthIndex }) => ({
        type: 'scatter',
        mode: 'lines',
        name: depth,
        x: times,
        y: data.values.map((row) => row[depthIndex]),
        line: { color: COLOR_PALETTE[depthIndex % COLOR_PALETTE.length] },
        hovertemplate: `${depth}<br>time: %{x}<br>${meta.variable}: %{y}<extra></extra>`,
      }))
  )
}

export function buildTimeseriesLayout(meta: TimeseriesFigureMeta, params: TimeseriesParams): Partial<Layout> {
  return {
    title: { text: params.axis.title || defaultTitle(meta) },
    xaxis: {
      title: { text: params.axis.xlabel || `time [${params.timeUnit}]` },
      range: resolveRange(params.timeRange),
    },
    yaxis: { title: { text: params.axis.ylabel || meta.variable }, range: resolveRange(params.valueRange) },
    margin: { l: 70, r: 30, t: 60, b: 60 },
    showlegend: true,
    paper_bgcolor: '#f4f6fb',
    plot_bgcolor: 'white',
    font: { family: '-apple-system, "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif', size: 12 },
  }
}

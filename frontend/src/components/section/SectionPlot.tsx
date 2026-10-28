import { useMemo, useRef, useState } from 'react'
import type { Annotations, Data, Layout } from 'plotly.js'
import PlotlyChart, { type PlotlyChartHandle } from '../common/PlotlyChart'
import { DownloadIcon, ImageIcon, ResetIcon } from '../common/icons'
import { COLORMAP_STOPS } from '../../constants'
import type { Plane, SectionDataResponse, SectionParams } from '../../types'

const ASPECT_MIN = 1 / 3
const ASPECT_MAX = 3

const DEFAULT_POSITIONS = {
  title: { x: 0.5, y: 1.12 },
  xlabel: { x: 0.5, y: -0.16 },
  ylabel: { x: -0.12, y: 0.5 },
  vectorKey: { x: 0.88, y: 1.15 },
}

const SLICE_COORD_LABEL: Record<Plane, string> = { YZ: 'X', XZ: 'Y', XY: 'Z' }

type Props = {
  data: SectionDataResponse | null
  loading: boolean
  params: SectionParams
  datasetKey: string
}

function clamp(value: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, value))
}

function buildColorscale(params: SectionParams): [number, string][] {
  if (params.customColormap.enabled) {
    const { low, useMid, mid, high } = params.customColormap
    return useMid
      ? [
          [0, low],
          [0.5, mid],
          [1, high],
        ]
      : [
          [0, low],
          [1, high],
        ]
  }
  const stops = COLORMAP_STOPS[params.colormap] ?? COLORMAP_STOPS.viridis
  const n = stops.length - 1
  return stops.map((color, i) => [i / n, color])
}

function computeColorRange(data: SectionDataResponse, params: SectionParams): [number, number] {
  if (!params.colorRange.auto && params.colorRange.vmin != null && params.colorRange.vmax != null) {
    return [params.colorRange.vmin, params.colorRange.vmax]
  }
  return data.value_range
}

function computeAutoZRange(data: SectionDataResponse): [number, number] {
  let lo = Infinity
  let hi = -Infinity
  data.values.forEach((row, i) => {
    if (row.some((v) => v !== null)) {
      lo = Math.min(lo, data.v_coords[i])
      hi = Math.max(hi, data.v_coords[i])
    }
  })
  if (!Number.isFinite(lo)) {
    return [Math.min(...data.v_coords), Math.max(...data.v_coords)]
  }
  return [lo, Math.max(0, hi)]
}

function computeVRange(data: SectionDataResponse, params: SectionParams): [number, number] | undefined {
  if (data.v_label !== 'Z') return undefined
  if (!params.axis.zlim.auto && params.axis.zlim.min != null && params.axis.zlim.max != null) {
    return [params.axis.zlim.min, params.axis.zlim.max]
  }
  return computeAutoZRange(data)
}

// Plotly の yaxis.scaleratio は「x軸の単位あたりピクセル数」に対する倍率であり、
// 画面上に実際に表示される縦横比（desiredAspect）そのものではない。
// desiredAspect = rawAspect(データの縦横比) * scaleratio という関係になるため、
// scaleratio = desiredAspect / rawAspect を返す必要がある。
function computeAspectRatio(data: SectionDataResponse, params: SectionParams, vRange?: [number, number]): number {
  const hExtent = Math.max(...data.h_coords) - Math.min(...data.h_coords) || 1
  const [vLo, vHi] = vRange ?? [Math.min(...data.v_coords), Math.max(...data.v_coords)]
  const vExtent = Math.max(vHi - vLo, 1e-6)
  const rawAspect = vExtent / hExtent

  const desiredAspect = params.axis.aspect.auto
    ? clamp(rawAspect, ASPECT_MIN, ASPECT_MAX)
    : params.axis.aspect.ratio && params.axis.aspect.ratio > 0
      ? params.axis.aspect.ratio
      : 1

  return desiredAspect / rawAspect
}

function buildVectorTraces(
  data: SectionDataResponse,
  params: SectionParams,
  hExtent: number,
): { traces: Data[]; maxMag: number } | null {
  if (!params.vectors.show || !data.vector_h || !data.vector_v) return null

  const skip = Math.max(1, params.vectors.skip)
  const points: { h: number; v: number; u: number; w: number }[] = []
  for (let i = 0; i < data.v_coords.length; i += skip) {
    const rowU = data.vector_h[i]
    const rowW = data.vector_v[i]
    if (!rowU || !rowW) continue
    for (let j = 0; j < data.h_coords.length; j += skip) {
      const u = rowU[j]
      const w = rowW[j]
      if (u == null || w == null) continue
      points.push({ h: data.h_coords[j], v: data.v_coords[i], u, w })
    }
  }
  if (points.length === 0) return null

  const maxMag = points.reduce((m, p) => Math.max(m, Math.hypot(p.u, p.w)), 0)
  const lengthPerUnit =
    params.vectors.scale && params.vectors.scale > 0
      ? params.vectors.scale
      : maxMag > 0
        ? (0.08 * hExtent) / maxMag
        : 1

  const shaftX: (number | null)[] = []
  const shaftY: (number | null)[] = []
  const headX: number[] = []
  const headY: number[] = []
  const headAngle: number[] = []

  for (const p of points) {
    const tipH = p.h + p.u * lengthPerUnit
    const tipV = p.v + p.w * lengthPerUnit
    shaftX.push(p.h, tipH, null)
    shaftY.push(p.v, tipV, null)
    headX.push(tipH)
    headY.push(tipV)
    headAngle.push((Math.atan2(p.u, p.w) * 180) / Math.PI)
  }

  const shaftTrace: Data = {
    x: shaftX,
    y: shaftY,
    type: 'scatter',
    mode: 'lines',
    line: { color: 'black', width: params.vectors.width },
    hoverinfo: 'skip',
    showlegend: false,
  }
  const headTrace = {
    x: headX,
    y: headY,
    type: 'scatter',
    mode: 'markers',
    marker: { symbol: 'triangle-up', size: params.vectors.headWidth, angle: headAngle, color: 'black' },
    hoverinfo: 'skip',
    showlegend: false,
  } as unknown as Data

  return { traces: [shaftTrace, headTrace], maxMag }
}

function defaultTitle(params: SectionParams, data: SectionDataResponse): string {
  return `${params.variable} 分布（${params.plane}断面, ${SLICE_COORD_LABEL[params.plane]} = ${data.actual_coord.toFixed(1)} m）`
}

export default function SectionPlot({ data, loading, params, datasetKey }: Props) {
  const chartRef = useRef<PlotlyChartHandle>(null)
  const [resetCounter, setResetCounter] = useState(0)

  const { plotData, layout } = useMemo<{ plotData: Data[]; layout: Partial<Layout> }>(() => {
    if (!data) return { plotData: [], layout: {} }

    const [vmin, vmax] = computeColorRange(data, params)
    const vRange = computeVRange(data, params)
    const hExtent = Math.max(...data.h_coords) - Math.min(...data.h_coords) || 1
    const aspectRatio = computeAspectRatio(data, params, vRange)
    const cbarLabel = params.axis.unit ? `${params.variable} [${params.axis.unit}]` : params.variable

    const fillTrace: Data = {
      type: 'contour',
      x: data.h_coords,
      y: data.v_coords,
      z: data.values,
      zmin: vmin,
      zmax: vmax,
      connectgaps: false,
      colorscale: buildColorscale(params),
      contours: {
        coloring: 'fill',
        start: vmin,
        end: vmax,
        size: (vmax - vmin) / Math.max(1, params.fillLevels) || 1,
      },
      colorbar: { title: { text: cbarLabel, side: 'right' } },
      hovertemplate: `${data.h_label}: %{x}<br>${data.v_label}: %{y}<br>${params.variable}: %{z}<extra></extra>`,
    }

    const traces: Data[] = [fillTrace]

    if (params.showContourLines) {
      traces.push({
        type: 'contour',
        x: data.h_coords,
        y: data.v_coords,
        z: data.values,
        connectgaps: false,
        showscale: false,
        contours: {
          coloring: 'lines',
          start: vmin,
          end: vmax,
          size: (vmax - vmin) / Math.max(1, params.lineLevels) || 1,
        },
        line: { color: '#7d7d7d', width: 0.6 },
        hoverinfo: 'skip',
      })
    }

    const vectorResult = buildVectorTraces(data, params, hExtent)
    if (vectorResult) traces.push(...vectorResult.traces)

    const annotations: Partial<Annotations>[] = [
      {
        x: DEFAULT_POSITIONS.title.x,
        y: DEFAULT_POSITIONS.title.y,
        xref: 'paper',
        yref: 'paper',
        text: params.axis.title || defaultTitle(params, data),
        showarrow: false,
        font: { size: 15 },
      },
      {
        x: DEFAULT_POSITIONS.xlabel.x,
        y: DEFAULT_POSITIONS.xlabel.y,
        xref: 'paper',
        yref: 'paper',
        text: params.axis.xlabel || `${data.h_label} [m]`,
        showarrow: false,
        font: { size: 12 },
      },
      {
        x: DEFAULT_POSITIONS.ylabel.x,
        y: DEFAULT_POSITIONS.ylabel.y,
        xref: 'paper',
        yref: 'paper',
        text: params.axis.ylabel || `${data.v_label} [m]`,
        showarrow: false,
        font: { size: 12 },
        textangle: '-90',
      },
    ]

    if (vectorResult && vectorResult.maxMag > 0) {
      const rounded = Math.round(vectorResult.maxMag * 100) / 100
      annotations.push({
        x: DEFAULT_POSITIONS.vectorKey.x,
        y: DEFAULT_POSITIONS.vectorKey.y,
        xref: 'paper',
        yref: 'paper',
        text: `${rounded} m/s`,
        showarrow: true,
        arrowhead: 2,
        arrowsize: 1,
        ax: -36,
        ay: 0,
        font: { size: 11 },
      })
    }

    const newLayout: Partial<Layout> = {
      uirevision: `${datasetKey}::${resetCounter}`,
      margin: { l: 90, r: 70, t: 80, b: 80 },
      xaxis: { zeroline: false },
      yaxis: { zeroline: false, scaleanchor: 'x', scaleratio: aspectRatio, range: vRange },
      annotations,
      showlegend: false,
      paper_bgcolor: '#f4f6fb',
      plot_bgcolor: 'white',
      font: { family: '-apple-system, "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif', size: 12 },
    }

    return { plotData: traces, layout: newLayout }
  }, [data, params, datasetKey, resetCounter])

  const config = useMemo(
    () => ({
      scrollZoom: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['toImage' as const],
      responsive: true,
      edits: { annotationPosition: true, colorbarPosition: true },
    }),
    [],
  )

  async function handleDownload() {
    if (!chartRef.current) return
    await chartRef.current.downloadImage({
      filename: `${params.variable}_${params.plane}`,
      scale: params.exportScale,
    })
  }

  return (
    <div className="plot-card">
      <div className="plot-card__header">
        <h3>プレビュー</h3>
        <div className="plot-card__actions">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => setResetCounter((c) => c + 1)}
            disabled={!data}
            title="ドラッグで動かしたタイトル・軸ラベルの位置を元に戻す"
          >
            <ResetIcon className="btn-icon" />
            ラベル位置をリセット
          </button>
          <button type="button" className="btn-secondary" onClick={handleDownload} disabled={!data}>
            <DownloadIcon className="btn-icon" />
            PNGをダウンロード
          </button>
        </div>
      </div>

      <div className="plot-card__canvas">
        {loading && (
          <div className="plot-loading">
            <span className="spinner" />
            <span>読み込み中…</span>
          </div>
        )}
        {!loading && data && (
          <PlotlyChart
            ref={chartRef}
            data={plotData}
            layout={layout}
            config={config}
            style={{ width: '100%', height: '100%' }}
          />
        )}
        {!loading && !data && (
          <div className="plot-placeholder">
            <ImageIcon className="plot-placeholder__icon" />
            <span>ファイルをアップロードすると、ここに断面図が表示されます</span>
          </div>
        )}
      </div>

      {!loading && data && (
        <div className="plot-card__meta">
          <span className="chip">
            実座標 {data.actual_coord.toFixed(2)}（index={data.actual_index}）
          </span>
          <span className="chip">
            値範囲 {data.value_range[0].toFixed(3)} 〜 {data.value_range[1].toFixed(3)}
          </span>
        </div>
      )}
    </div>
  )
}

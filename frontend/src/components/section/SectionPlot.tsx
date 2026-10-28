import { useMemo, useRef, useState } from 'react'
import type { Annotations, Data, Layout } from 'plotly.js'
import PlotlyChart, { type PlotlyChartHandle } from '../common/PlotlyChart'
import { DownloadIcon, ImageIcon, ResetIcon } from '../common/icons'
import type { SectionDataResponse, SectionParams } from '../../types'
import {
  buildColorscale,
  buildVectorTraces,
  computeAspectRatio,
  computeColorRange,
  computeVRange,
  defaultTitle,
} from './sectionFigure'

const DEFAULT_POSITIONS = {
  title: { x: 0.5, y: 1.12 },
  xlabel: { x: 0.5, y: -0.16 },
  ylabel: { x: -0.12, y: 0.5 },
  vectorKey: { x: 0.88, y: 1.15 },
}

type Props = {
  data: SectionDataResponse | null
  loading: boolean
  params: SectionParams
  datasetKey: string
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

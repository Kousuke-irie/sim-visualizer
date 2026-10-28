import { useMemo, useRef } from 'react'
import type { Data, Layout } from 'plotly.js'
import PlotlyChart, { type PlotlyChartHandle } from '../common/PlotlyChart'
import { DownloadIcon, ImageIcon } from '../common/icons'
import { COLOR_PALETTE } from '../../constants'
import type { DatMeta, TimeseriesDataResponse, TimeseriesParams } from '../../types'

type Meta = Pick<DatMeta, 'depths' | 'variable'>

type Props = {
  meta: Meta
  data: TimeseriesDataResponse | null
  loading: boolean
  params: TimeseriesParams
}

function defaultTitle(meta: Meta): string {
  return `${meta.variable} 時系列（深度別）`
}

export default function TimeseriesPlot({ meta, data, loading, params }: Props) {
  const chartRef = useRef<PlotlyChartHandle>(null)

  const { plotData, layout } = useMemo<{ plotData: Data[]; layout: Partial<Layout> }>(() => {
    if (!data) return { plotData: [], layout: {} }

    const unitDivisor = params.timeUnit === 'hour' ? 3600 : 1
    const times = data.times.map((t) => t / unitDivisor)

    const traces: Data[] = meta.depths
      .map((depth, depthIndex) => ({ depth, depthIndex }))
      .filter(({ depth }) => params.selectedDepths.includes(depth))
      .map(({ depth, depthIndex }) => ({
        type: 'scatter',
        mode: 'lines',
        name: depth,
        x: times,
        y: data.values.map((row) => row[depthIndex]),
        line: { color: COLOR_PALETTE[depthIndex % COLOR_PALETTE.length] },
        hovertemplate: `${depth}<br>time: %{x}<br>${meta.variable}: %{y}<extra></extra>`,
      }))

    const xRange: [number, number] | undefined =
      !params.timeRange.auto && params.timeRange.min != null && params.timeRange.max != null
        ? [params.timeRange.min, params.timeRange.max]
        : undefined
    const yRange: [number, number] | undefined =
      !params.valueRange.auto && params.valueRange.min != null && params.valueRange.max != null
        ? [params.valueRange.min, params.valueRange.max]
        : undefined

    const newLayout: Partial<Layout> = {
      title: { text: params.axis.title || defaultTitle(meta) },
      xaxis: { title: { text: params.axis.xlabel || `time [${params.timeUnit}]` }, range: xRange },
      yaxis: { title: { text: params.axis.ylabel || meta.variable }, range: yRange },
      margin: { l: 70, r: 30, t: 60, b: 60 },
      showlegend: true,
      paper_bgcolor: '#f4f6fb',
      plot_bgcolor: 'white',
      font: { family: '-apple-system, "Hiragino Kaku Gothic ProN", "Yu Gothic", sans-serif', size: 12 },
    }

    return { plotData: traces, layout: newLayout }
  }, [data, meta, params])

  const config = useMemo(
    () => ({
      scrollZoom: true,
      displaylogo: false,
      modeBarButtonsToRemove: ['toImage' as const],
      responsive: true,
    }),
    [],
  )

  async function handleDownload() {
    if (!chartRef.current) return
    await chartRef.current.downloadImage({ filename: `${meta.variable}_timeseries`, scale: params.exportScale })
  }

  return (
    <div className="plot-card">
      <div className="plot-card__header">
        <h3>プレビュー</h3>
        <div className="plot-card__actions">
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
            <span>ファイルをアップロードすると、ここに時系列グラフが表示されます</span>
          </div>
        )}
      </div>
    </div>
  )
}

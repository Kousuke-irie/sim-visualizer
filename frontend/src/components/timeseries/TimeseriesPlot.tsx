import { useMemo, useRef } from 'react'
import type { Data, Layout } from 'plotly.js'
import PlotlyChart, { type PlotlyChartHandle } from '../common/PlotlyChart'
import { DownloadIcon, ImageIcon } from '../common/icons'
import type { TimeseriesDataResponse, TimeseriesParams } from '../../types'
import { buildTimeseriesLayout, buildTimeseriesTraces, type TimeseriesFigureMeta } from './timeseriesFigure'

type Meta = TimeseriesFigureMeta

type Props = {
  meta: Meta
  data: TimeseriesDataResponse | null
  loading: boolean
  params: TimeseriesParams
  // 指定すると、data から作る代わりにこのトレースを描く（比較タブの A・B 重ね描きで使う）
  traces?: Data[]
}

export default function TimeseriesPlot({ meta, data, loading, params, traces }: Props) {
  const chartRef = useRef<PlotlyChartHandle>(null)

  const { plotData, layout } = useMemo<{ plotData: Data[]; layout: Partial<Layout> }>(() => {
    if (!data) return { plotData: [], layout: {} }
    return {
      plotData: traces ?? buildTimeseriesTraces(meta, data, params),
      layout: buildTimeseriesLayout(meta, params),
    }
  }, [data, meta, params, traces])

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

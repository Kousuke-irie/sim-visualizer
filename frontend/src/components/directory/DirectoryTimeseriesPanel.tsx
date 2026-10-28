import { useEffect, useMemo, useState } from 'react'
import PointParamSelect from './PointParamSelect'
import ErrorBanner from '../common/ErrorBanner'
import TimeseriesControls from '../timeseries/TimeseriesControls'
import TimeseriesPlot from '../timeseries/TimeseriesPlot'
import { reconcileTimeseriesParams } from '../timeseries/timeseriesParams'
import { fetchDirectoryTimeseriesData } from '../../api/client'
import { useLatestRequest } from '../../hooks/useLatestRequest'
import type { DirectoryMeta, DirectoryTimeseriesRequest, TimeseriesParams } from '../../types'

type Props = { meta: DirectoryMeta }

function firstPointOf(meta: DirectoryMeta, param: string): string {
  return meta.timeseries.by_param[param]?.[0] ?? ''
}

// ディレクトリモードの「時系列」タブ。地点 × パラメータを選んで hist の深度別時系列を描く
export default function DirectoryTimeseriesPanel({ meta }: Props) {
  const [param, setParam] = useState(() => meta.timeseries.params[0] ?? '')
  const [point, setPoint] = useState(() => firstPointOf(meta, meta.timeseries.params[0] ?? ''))
  // 最初の取得が成功するまで null（深度の一覧がデータから決まるため）
  const [params, setParams] = useState<TimeseriesParams | null>(null)

  const dirId = meta.dir_id
  const request = useMemo<DirectoryTimeseriesRequest | null>(
    () => (param && point ? { dir_id: dirId, param, point } : null),
    [dirId, param, point],
  )
  const { data, loading, error } = useLatestRequest(request, fetchDirectoryTimeseriesData)

  // 取り直したら、見た目の設定は残したまま深度の選択だけを新しいデータに合わせる
  useEffect(() => {
    if (data) setParams((prev) => reconcileTimeseriesParams(prev, data.depths))
  }, [data])

  function handlePointParamChange(patch: { param?: string; point?: string }) {
    if (patch.param !== undefined) {
      setParam(patch.param)
      setPoint(firstPointOf(meta, patch.param))
    } else if (patch.point !== undefined) {
      setPoint(patch.point)
    }
  }

  // ラベルは表示中のデータに合わせる（取得中に選択だけ先に変わっても、古いグラフに新しい名前を付けない）
  const plotMeta = useMemo(() => ({ depths: data?.depths ?? [], variable: data?.variable ?? param }), [data, param])

  function updateParams(patch: Partial<TimeseriesParams>) {
    setParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  return (
    <>
      {/* エラー表示と地点・パラメータの選択は params を待たずに出し、初回取得に失敗しても選び直せるようにする */}
      <ErrorBanner message={error} />
      <PointParamSelect
        timeseries={meta.timeseries}
        points={meta.points}
        param={param}
        point={point}
        onChange={handlePointParamChange}
      />
      {params && (
        <div className="section-view__body">
          <TimeseriesControls meta={plotMeta} params={params} onChange={updateParams} />
          <TimeseriesPlot meta={plotMeta} data={data} loading={loading} params={params} />
        </div>
      )}
    </>
  )
}

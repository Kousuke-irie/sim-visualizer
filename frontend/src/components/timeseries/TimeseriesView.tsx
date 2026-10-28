import { useEffect, useState } from 'react'
import FileUpload from '../common/FileUpload'
import ErrorBanner from '../common/ErrorBanner'
import TimeseriesControls from './TimeseriesControls'
import TimeseriesPlot from './TimeseriesPlot'
import { uploadDat, fetchTimeseriesData } from '../../api/client'
import type { DatMeta, TimeseriesDataResponse, TimeseriesParams } from '../../types'
import { createDefaultTimeseriesParams } from './timeseriesParams'

export default function TimeseriesView() {
  const [meta, setMeta] = useState<DatMeta | null>(null)
  const [data, setData] = useState<TimeseriesDataResponse | null>(null)
  const [params, setParams] = useState<TimeseriesParams | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [dataError, setDataError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadError(null)
    setData(null)
    try {
      const newMeta = await uploadDat(file)
      setMeta(newMeta)
      setParams(createDefaultTimeseriesParams(newMeta.depths))
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'アップロードに失敗しました')
    } finally {
      setUploading(false)
    }
  }

  useEffect(() => {
    if (!meta) return
    let cancelled = false
    setLoading(true)
    setDataError(null)
    fetchTimeseriesData(meta.file_id)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch((err: Error) => {
        if (!cancelled) setDataError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [meta])

  function updateParams(patch: Partial<TimeseriesParams>) {
    setParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  return (
    <div className="section-view">
      <header className="section-view__header">
        <h2>時系列ビュー</h2>
        <FileUpload accept=".dat" label="時系列ファイル (.dat) を選択" onSelect={handleUpload} disabled={uploading} />
      </header>

      <ErrorBanner message={uploadError} onDismiss={() => setUploadError(null)} />
      <ErrorBanner message={dataError} />

      {meta && (
        <div className="section-view__meta">
          <span className="chip chip--muted">変数 {meta.variable}</span>
          <span className="chip chip--muted">
            格子 i={meta.grid.i} j={meta.grid.j} n={meta.grid.n} h={meta.grid.h}m
          </span>
          <span className="chip chip--muted">深度 {meta.depths.length}点</span>
          <span className="chip chip--muted">時刻 {meta.n_times}点</span>
        </div>
      )}

      {meta && params && (
        <div className="section-view__body">
          <TimeseriesControls meta={meta} params={params} onChange={updateParams} />
          <TimeseriesPlot meta={meta} data={data} loading={loading} params={params} />
        </div>
      )}
    </div>
  )
}

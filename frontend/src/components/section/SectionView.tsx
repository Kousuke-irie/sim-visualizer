import { useMemo, useState } from 'react'
import FileUpload from '../common/FileUpload'
import ErrorBanner from '../common/ErrorBanner'
import SectionPlot from './SectionPlot'
import SectionControls from './SectionControls'
import { uploadPlt } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useSectionData } from '../../hooks/useRender'
import type { PltMeta, Plane, SectionDataRequest, SectionParams } from '../../types'
import { COORD_VAR_LABEL, PLANE_AXIS, createDefaultSectionParams, midIndex, sliceAxisSize } from './sectionDefaults'

export default function SectionView() {
  const [meta, setMeta] = useState<PltMeta | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [params, setParams] = useState<SectionParams | null>(null)

  async function handleUpload(file: File) {
    setUploading(true)
    setUploadError(null)
    try {
      const newMeta = await uploadPlt(file)
      setMeta(newMeta)
      setParams(createDefaultSectionParams(newMeta.dims, newMeta.variables, 'YZ'))
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'アップロードに失敗しました')
    } finally {
      setUploading(false)
    }
  }

  function updateParams(patch: Partial<SectionParams>) {
    setParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  function handlePlaneChange(plane: Plane) {
    if (!meta) return
    updateParams({ plane, sliceIndex: midIndex(sliceAxisSize(meta.dims, plane)) })
  }

  // データ取得（サーバー往復）が必要なのは平面・スライス位置・変数が変わったときだけ。
  // 色・レベル数・ラベル・ベクトル見た目などのスタイル変更はここに影響せず、
  // SectionPlot 側でクライアントのみで即時反映される。
  // 依存配列を「通信に関わる値」だけに絞るため、先にプリミティブとして取り出しておく
  const fileId = meta?.file_id
  const plane = params?.plane
  const sliceIndex = params?.sliceIndex
  const variable = params?.variable
  const dataRequest = useMemo<SectionDataRequest | null>(() => {
    if (fileId === undefined || plane === undefined || sliceIndex === undefined || variable === undefined) return null
    return { file_id: fileId, plane, slice_index: sliceIndex, variable, include_vectors: true }
  }, [fileId, plane, sliceIndex, variable])

  const debouncedRequest = useDebounced(dataRequest, 150)
  const { data, loading, error: dataError } = useSectionData(debouncedRequest)

  const axisSize = meta && params ? sliceAxisSize(meta.dims, params.plane) : 0
  const datasetKey = meta && params ? `${meta.file_id}-${params.plane}-${params.sliceIndex}-${params.variable}` : ''

  return (
    <div className="section-view">
      <header className="section-view__header">
        <h2>断面ビュー</h2>
        <FileUpload accept=".plt" label="断面ファイル (.plt) を選択" onSelect={handleUpload} disabled={uploading} />
      </header>

      <ErrorBanner message={uploadError} onDismiss={() => setUploadError(null)} />
      <ErrorBanner message={dataError} />

      {meta && (
        <div className="section-view__meta">
          <span className="chip chip--muted">変数 {meta.variables.length}種</span>
          <span className="chip chip--muted">
            格子 I={meta.dims.I} J={meta.dims.J} K={meta.dims.K}
          </span>
        </div>
      )}

      {meta && params && (
        <div className="section-view__body">
          <SectionControls
            meta={meta}
            params={params}
            axisSize={axisSize}
            axisCoordLabel={COORD_VAR_LABEL[PLANE_AXIS[params.plane]]}
            onPlaneChange={handlePlaneChange}
            onChange={updateParams}
          />
          <SectionPlot data={data} loading={loading} params={params} datasetKey={datasetKey} />
        </div>
      )}
    </div>
  )
}

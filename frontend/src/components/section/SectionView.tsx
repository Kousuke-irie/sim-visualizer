import { useMemo, useState } from 'react'
import FileUpload from '../common/FileUpload'
import ErrorBanner from '../common/ErrorBanner'
import SectionPlot from './SectionPlot'
import SectionControls from './SectionControls'
import { uploadPlt } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useSectionData } from '../../hooks/useRender'
import type { Dims, PltMeta, Plane, SectionDataRequest, SectionParams } from '../../types'

const PLANE_AXIS: Record<Plane, keyof Dims> = { YZ: 'I', XZ: 'J', XY: 'K' }
const COORD_VAR_LABEL: Record<keyof Dims, string> = { I: 'X', J: 'Y', K: 'Z' }

function defaultVariable(variables: string[]): string {
  return variables.find((v) => !['X', 'Y', 'Z'].includes(v)) ?? variables[0]
}

function midIndex(size: number): number {
  return Math.max(0, Math.floor((size - 1) / 2))
}

function defaultParams(meta: PltMeta, plane: Plane): SectionParams {
  const size = meta.dims[PLANE_AXIS[plane]]
  return {
    plane,
    sliceIndex: midIndex(size),
    variable: defaultVariable(meta.variables),
    colormap: 'viridis',
    customColormap: { enabled: false, low: '#1b4965', useMid: false, mid: '#2a9d8f', high: '#e76f51' },
    fillLevels: 30,
    lineLevels: 10,
    showContourLines: true,
    colorRange: { auto: true },
    vectors: { show: true, skip: 2, width: 1.5, headWidth: 8 },
    axis: { zlim: { auto: true }, aspect: { auto: true, ratio: 1 } },
    exportScale: 2,
  }
}

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
      setParams(defaultParams(newMeta, 'YZ'))
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
    const size = meta.dims[PLANE_AXIS[plane]]
    updateParams({ plane, sliceIndex: midIndex(size) })
  }

  // データ取得（サーバー往復）が必要なのは平面・スライス位置・変数が変わったときだけ。
  // 色・レベル数・ラベル・ベクトル見た目などのスタイル変更はここに影響せず、
  // SectionPlot 側でクライアントのみで即時反映される。
  const dataRequest = useMemo<SectionDataRequest | null>(() => {
    if (!meta || !params) return null
    return {
      file_id: meta.file_id,
      plane: params.plane,
      slice_index: params.sliceIndex,
      variable: params.variable,
      include_vectors: true,
    }
  }, [meta, params?.plane, params?.sliceIndex, params?.variable])

  const debouncedRequest = useDebounced(dataRequest, 150)
  const { data, loading, error: dataError } = useSectionData(debouncedRequest)

  const axisSize = meta && params ? meta.dims[PLANE_AXIS[params.plane]] : 0
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

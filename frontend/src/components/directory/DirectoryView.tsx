import { useEffect, useMemo, useState } from 'react'
import DirectoryOpen from './DirectoryOpen'
import TimeSlider from './TimeSlider'
import PointParamSelect from './PointParamSelect'
import ErrorBanner from '../common/ErrorBanner'
import SectionControls from '../section/SectionControls'
import SectionPlot from '../section/SectionPlot'
import TimeseriesControls from '../timeseries/TimeseriesControls'
import TimeseriesPlot from '../timeseries/TimeseriesPlot'
import { reconcileTimeseriesParams } from '../timeseries/timeseriesParams'
import {
  COORD_VAR_LABEL,
  PLANE_AXIS,
  createDefaultSectionParams,
  midIndex,
  sliceAxisSize,
} from '../section/sectionDefaults'
import { fetchDirectorySectionData, fetchDirectoryTimeseriesData, openDirectory } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useLatestRequest } from '../../hooks/useLatestRequest'
import type {
  DirectoryMeta,
  DirectorySectionDataRequest,
  DirectoryTimeseriesRequest,
  Plane,
  SectionParams,
  TimeseriesParams,
  TimeUnit,
} from '../../types'

type SubTab = 'section' | 'timeseries'

export default function DirectoryView() {
  const [meta, setMeta] = useState<DirectoryMeta | null>(null)
  const [opening, setOpening] = useState(false)
  const [openError, setOpenError] = useState<string | null>(null)
  const [subTab, setSubTab] = useState<SubTab>('section')

  // 空間分布サブビューの状態
  const [framePosition, setFramePosition] = useState(0)
  const [frameTimeUnit, setFrameTimeUnit] = useState<TimeUnit>('sec')
  const [sectionParams, setSectionParams] = useState<SectionParams | null>(null)

  // 時系列サブビューの状態
  const [tsParam, setTsParam] = useState('')
  const [tsPoint, setTsPoint] = useState('')
  const [tsParams, setTsParams] = useState<TimeseriesParams | null>(null)

  async function handleOpen(path: string) {
    setOpening(true)
    setOpenError(null)
    try {
      const newMeta = await openDirectory(path)
      setMeta(newMeta)
      setSubTab('section')
      setFramePosition(midIndex(newMeta.plt_frames.length))
      setFrameTimeUnit('sec')
      setSectionParams(createDefaultSectionParams(newMeta.plt_dims, newMeta.plt_variables, 'YZ'))
      const firstParam = newMeta.timeseries.params[0] ?? ''
      const firstPoint = newMeta.timeseries.by_param[firstParam]?.[0] ?? ''
      setTsParam(firstParam)
      setTsPoint(firstPoint)
      setTsParams(null)
    } catch (err) {
      setOpenError(err instanceof Error ? err.message : 'ディレクトリを開けませんでした')
    } finally {
      setOpening(false)
    }
  }

  function updateSectionParams(patch: Partial<SectionParams>) {
    setSectionParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  function handlePlaneChange(plane: Plane) {
    if (!meta) return
    updateSectionParams({ plane, sliceIndex: midIndex(sliceAxisSize(meta.plt_dims, plane)) })
  }

  function updateTsParams(patch: Partial<TimeseriesParams>) {
    setTsParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  const currentFrame = meta?.plt_frames[framePosition]

  // データ取得（サーバー往復）が必要なのは平面・スライス位置・変数・フレームが変わったときだけ。
  // 色・レベル数などのスタイル変更は SectionPlot 側でクライアントのみ即時反映される（DESIGN.md 7-1節の方針を踏襲）。
  // 依存配列を「通信に関わる値」だけに絞るため、先にプリミティブとして取り出しておく
  const dirId = meta?.dir_id
  const frameIndex = currentFrame?.index
  const plane = sectionParams?.plane
  const sliceIndex = sectionParams?.sliceIndex
  const variable = sectionParams?.variable
  const sectionDataRequest = useMemo<DirectorySectionDataRequest | null>(() => {
    if (
      dirId === undefined ||
      frameIndex === undefined ||
      plane === undefined ||
      sliceIndex === undefined ||
      variable === undefined
    ) {
      return null
    }
    return { dir_id: dirId, frame_index: frameIndex, plane, slice_index: sliceIndex, variable, include_vectors: true }
  }, [dirId, frameIndex, plane, sliceIndex, variable])

  const debouncedSectionRequest = useDebounced(sectionDataRequest, 150)
  const {
    data: sectionData,
    loading: sectionLoading,
    error: sectionError,
  } = useLatestRequest(debouncedSectionRequest, fetchDirectorySectionData)

  const tsRequest = useMemo<DirectoryTimeseriesRequest | null>(
    () => (dirId && tsParam && tsPoint ? { dir_id: dirId, param: tsParam, point: tsPoint } : null),
    [dirId, tsParam, tsPoint],
  )
  const { data: tsData, loading: tsLoading, error: tsError } = useLatestRequest(tsRequest, fetchDirectoryTimeseriesData)

  // 取り直したら、見た目の設定は残したまま深度の選択だけを新しいデータに合わせる
  useEffect(() => {
    if (tsData) setTsParams((prev) => reconcileTimeseriesParams(prev, tsData.depths))
  }, [tsData])

  function handlePointParamChange(patch: { param?: string; point?: string }) {
    if (!meta) return
    if (patch.param !== undefined) {
      const nextPoint = meta.timeseries.by_param[patch.param]?.[0] ?? ''
      setTsParam(patch.param)
      setTsPoint(nextPoint)
    } else if (patch.point !== undefined) {
      setTsPoint(patch.point)
    }
  }

  const axisSize = meta && sectionParams ? sliceAxisSize(meta.plt_dims, sectionParams.plane) : 0
  const datasetKey =
    meta && sectionParams && currentFrame
      ? `${meta.dir_id}-${sectionParams.plane}-${sectionParams.sliceIndex}-${sectionParams.variable}-${currentFrame.index}`
      : ''

  const tsMeta = { depths: tsData?.depths ?? [], variable: tsParam }

  return (
    <div className="section-view">
      <header className="section-view__header">
        <h2>ディレクトリモード</h2>
        <DirectoryOpen onOpen={handleOpen} disabled={opening} />
      </header>

      <ErrorBanner message={openError} onDismiss={() => setOpenError(null)} />

      {meta && (
        <div className="section-view__meta">
          <span className="chip chip--muted">{meta.root}</span>
          <span className="chip chip--muted">フレーム数 {meta.plt_frames.length}</span>
          <span className="chip chip--muted">地点数 {meta.points.length}</span>
          <span className="chip chip--muted">
            計算期間 0〜{meta.input.endtime.toFixed(0)}s（plt間隔 {meta.input.ifit2.toFixed(0)}s）
          </span>
        </div>
      )}

      {meta && (
        <div
          className="segmented app__tabs"
          role="radiogroup"
          aria-label="ディレクトリモードの表示切替"
          style={{ marginBottom: '1.25rem' }}
        >
          <label className={`segmented__option ${subTab === 'section' ? 'is-active' : ''}`}>
            <input
              type="radio"
              name="directory-subtab"
              checked={subTab === 'section'}
              onChange={() => setSubTab('section')}
            />
            空間分布
          </label>
          <label className={`segmented__option ${subTab === 'timeseries' ? 'is-active' : ''}`}>
            <input
              type="radio"
              name="directory-subtab"
              checked={subTab === 'timeseries'}
              onChange={() => setSubTab('timeseries')}
            />
            時系列
          </label>
        </div>
      )}

      {meta && sectionParams && subTab === 'section' && (
        <>
          <ErrorBanner message={sectionError} />
          <TimeSlider
            frames={meta.plt_frames}
            position={framePosition}
            onPositionChange={setFramePosition}
            timeUnit={frameTimeUnit}
            onTimeUnitChange={setFrameTimeUnit}
          />
          <div className="section-view__body">
            <SectionControls
              meta={{ variables: meta.plt_variables }}
              params={sectionParams}
              axisSize={axisSize}
              axisCoordLabel={COORD_VAR_LABEL[PLANE_AXIS[sectionParams.plane]]}
              onPlaneChange={handlePlaneChange}
              onChange={updateSectionParams}
            />
            <SectionPlot data={sectionData} loading={sectionLoading} params={sectionParams} datasetKey={datasetKey} />
          </div>
        </>
      )}

      {/* tsParams は最初の取得が成功するまで null。エラー表示と地点・パラメータの選択はそれを待たずに出し、
          初回取得に失敗しても別の組み合わせを選び直せるようにする */}
      {meta && subTab === 'timeseries' && (
        <>
          <ErrorBanner message={tsError} />
          <PointParamSelect
            timeseries={meta.timeseries}
            points={meta.points}
            param={tsParam}
            point={tsPoint}
            onChange={handlePointParamChange}
          />
          {tsParams && (
            <div className="section-view__body">
              <TimeseriesControls meta={tsMeta} params={tsParams} onChange={updateTsParams} />
              <TimeseriesPlot
                meta={tsMeta}
                data={tsData ? { times: tsData.times, values: tsData.values } : null}
                loading={tsLoading}
                params={tsParams}
              />
            </div>
          )}
        </>
      )}
    </div>
  )
}

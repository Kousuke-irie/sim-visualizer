import { useEffect, useMemo, useState } from 'react'
import DirectoryOpen from './DirectoryOpen'
import TimeSlider from './TimeSlider'
import PointParamSelect from './PointParamSelect'
import ErrorBanner from '../common/ErrorBanner'
import SectionControls from '../section/SectionControls'
import SectionPlot from '../section/SectionPlot'
import TimeseriesControls from '../timeseries/TimeseriesControls'
import TimeseriesPlot from '../timeseries/TimeseriesPlot'
import { fetchDirectoryTimeseriesData, openDirectory } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useDirectorySectionData } from '../../hooks/useRender'
import type {
  Dims,
  DirectoryMeta,
  DirectorySectionDataRequest,
  DirectoryTimeseriesResponse,
  Plane,
  SectionParams,
  TimeseriesParams,
  TimeUnit,
} from '../../types'

const PLANE_AXIS: Record<Plane, keyof Dims> = { YZ: 'I', XZ: 'J', XY: 'K' }
const COORD_VAR_LABEL: Record<keyof Dims, string> = { I: 'X', J: 'Y', K: 'Z' }

type SubTab = 'section' | 'timeseries'

function defaultVariable(variables: string[]): string {
  return variables.find((v) => !['X', 'Y', 'Z'].includes(v)) ?? variables[0]
}

function midIndex(size: number): number {
  return Math.max(0, Math.floor((size - 1) / 2))
}

function defaultSectionParams(meta: DirectoryMeta, plane: Plane): SectionParams {
  const size = meta.plt_dims[PLANE_AXIS[plane]]
  return {
    plane,
    sliceIndex: midIndex(size),
    variable: defaultVariable(meta.plt_variables),
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

function defaultTimeseriesParams(depths: string[]): TimeseriesParams {
  return {
    selectedDepths: [...depths],
    timeUnit: 'sec',
    timeRange: { auto: true },
    valueRange: { auto: true },
    axis: {},
    exportScale: 2,
  }
}

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
  const [tsData, setTsData] = useState<DirectoryTimeseriesResponse | null>(null)
  const [tsLoading, setTsLoading] = useState(false)
  const [tsError, setTsError] = useState<string | null>(null)
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
      setSectionParams(defaultSectionParams(newMeta, 'YZ'))
      const firstParam = newMeta.timeseries.params[0] ?? ''
      const firstPoint = newMeta.timeseries.by_param[firstParam]?.[0] ?? ''
      setTsParam(firstParam)
      setTsPoint(firstPoint)
      setTsData(null)
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
    const size = meta.plt_dims[PLANE_AXIS[plane]]
    updateSectionParams({ plane, sliceIndex: midIndex(size) })
  }

  function updateTsParams(patch: Partial<TimeseriesParams>) {
    setTsParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  const currentFrame = meta?.plt_frames[framePosition]

  // データ取得（サーバー往復）が必要なのは平面・スライス位置・変数・フレームが変わったときだけ。
  // 色・レベル数などのスタイル変更は SectionPlot 側でクライアントのみ即時反映される（DESIGN.md 7-1節の方針を踏襲）。
  const sectionDataRequest = useMemo<DirectorySectionDataRequest | null>(() => {
    if (!meta || !sectionParams || !currentFrame) return null
    return {
      dir_id: meta.dir_id,
      frame_index: currentFrame.index,
      plane: sectionParams.plane,
      slice_index: sectionParams.sliceIndex,
      variable: sectionParams.variable,
      include_vectors: true,
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta?.dir_id, sectionParams?.plane, sectionParams?.sliceIndex, sectionParams?.variable, currentFrame?.index])

  const debouncedSectionRequest = useDebounced(sectionDataRequest, 150)
  const {
    data: sectionData,
    loading: sectionLoading,
    error: sectionError,
  } = useDirectorySectionData(debouncedSectionRequest)

  useEffect(() => {
    if (!meta || !tsParam || !tsPoint) return
    let cancelled = false
    setTsLoading(true)
    setTsError(null)
    fetchDirectoryTimeseriesData({ dir_id: meta.dir_id, param: tsParam, point: tsPoint })
      .then((res) => {
        if (cancelled) return
        setTsData(res)
        setTsParams(defaultTimeseriesParams(res.depths))
      })
      .catch((err: Error) => {
        if (!cancelled) setTsError(err.message)
      })
      .finally(() => {
        if (!cancelled) setTsLoading(false)
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [meta?.dir_id, tsParam, tsPoint])

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

  const axisSize = meta && sectionParams ? meta.plt_dims[PLANE_AXIS[sectionParams.plane]] : 0
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
        <div className="segmented app__tabs" role="radiogroup" aria-label="ディレクトリモードの表示切替" style={{ marginBottom: '1.25rem' }}>
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

      {meta && tsParams && subTab === 'timeseries' && (
        <>
          <ErrorBanner message={tsError} />
          <PointParamSelect
            timeseries={meta.timeseries}
            points={meta.points}
            param={tsParam}
            point={tsPoint}
            onChange={handlePointParamChange}
          />
          <div className="section-view__body">
            <TimeseriesControls meta={tsMeta} params={tsParams} onChange={updateTsParams} />
            <TimeseriesPlot
              meta={tsMeta}
              data={tsData ? { times: tsData.times, values: tsData.values } : null}
              loading={tsLoading}
              params={tsParams}
            />
          </div>
        </>
      )}
    </div>
  )
}

import { useEffect, useMemo, useState } from 'react'
import TimeSlider from './TimeSlider'
import { buildDiffView, buildOverlayTraces, buildPairViews, runLabel, unionDepths } from './compareFigure'
import ErrorBanner from '../common/ErrorBanner'
import SectionControls from '../section/SectionControls'
import SectionPlot from '../section/SectionPlot'
import {
  COORD_VAR_LABEL,
  PLANE_AXIS,
  createDefaultSectionParams,
  defaultVariable,
  midIndex,
  sliceAxisSize,
} from '../section/sectionDefaults'
import TimeseriesControls from '../timeseries/TimeseriesControls'
import TimeseriesPlot from '../timeseries/TimeseriesPlot'
import { reconcileTimeseriesParams } from '../timeseries/timeseriesParams'
import { compareCheck, fetchCompareSection, fetchCompareTimeseries } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useLatestRequest } from '../../hooks/useLatestRequest'
import type {
  CompareCheckRequest,
  CompareSectionRequest,
  CompareTimeseriesRequest,
  DirectoryMeta,
  Plane,
  PltFrameMeta,
  SectionParams,
  TimeseriesParams,
  TimeUnit,
} from '../../types'

type Props = {
  runs: DirectoryMeta[]
  // 「元のランと比較」から開いたときの A・B（dir_id）。無ければ開いた順で決める
  initialA?: string
  initialB?: string
}

type CompareView = 'diff' | 'pair' | 'timeseries'

const VIEWS: { value: CompareView; label: string }[] = [
  { value: 'diff', label: '差分（B − A）' },
  { value: 'pair', label: 'A・B を並べる' },
  { value: 'timeseries', label: '地点時系列' },
]

// 差分は 0 中心の発散型、値そのものを並べるときは通常の連続型。表示ごとに別々に覚える（DESIGN_research_features.md §3.3）
const DEFAULT_COLORMAPS: Record<'diff' | 'pair', string> = { diff: 'RdBu_r', pair: 'viridis' }

// ディレクトリモードの「比較」タブ。開いたランから A・B を選び、同じ時刻・同じ断面（または同じ地点）で比べる
export default function DirectoryComparePanel({ runs, initialA, initialB }: Props) {
  // 既定は A = 先に開いたラン、B = 後から開いたラン
  const [aId, setAId] = useState(() => initialA ?? runs[runs.length - 2]?.dir_id ?? '')
  const [bId, setBId] = useState(() => initialB ?? runs[runs.length - 1]?.dir_id ?? '')
  // 同じディレクトリを開き直すと dir_id が変わる。選んでいたランが一覧から消えたら既定に戻す
  const a = runs.find((r) => r.dir_id === aId) ?? runs[runs.length - 2]
  const b = runs.find((r) => r.dir_id === bId) ?? runs[runs.length - 1]
  const [view, setView] = useState<CompareView>('diff')

  const checkRequest = useMemo<CompareCheckRequest | null>(
    () => (a && b && a.dir_id !== b.dir_id ? { dir_a: a.dir_id, dir_b: b.dir_id } : null),
    [a, b],
  )
  const { data: check, error: checkError } = useLatestRequest(checkRequest, compareCheck)
  const labels = useMemo(() => ({ a: a ? runLabel(a.root) : 'A', b: b ? runLabel(b.root) : 'B' }), [a, b])

  // ---- 断面（差分・並べる）----
  const [params, setParams] = useState<SectionParams | null>(null)
  const [colormaps, setColormaps] = useState(DEFAULT_COLORMAPS)
  // null の間は中央の時刻を表示する（共通の時刻が分かるまで位置を決められないため）
  const [timePosition, setTimePosition] = useState<number | null>(null)
  const [timeUnit, setTimeUnit] = useState<TimeUnit>('sec')

  // A・B を選び直して共通の変数が変わったら、それに合わせて初期化する（見た目の設定は残す）
  useEffect(() => {
    if (!check || !a) return
    setParams((prev) => {
      const base = prev ?? createDefaultSectionParams(a.plt_dims, check.common_variables, 'YZ')
      return check.common_variables.includes(base.variable)
        ? base
        : { ...base, variable: defaultVariable(check.common_variables) }
    })
  }, [check, a])

  // 時間スライダーは A・B の両方に出力がある時刻だけを並べる
  const frames = useMemo<PltFrameMeta[]>(
    () => (check ? check.common_times.map((t, i) => ({ file: '', index: i, time_sec: t })) : []),
    [check],
  )
  const position = check
    ? Math.min(timePosition ?? midIndex(check.common_times.length), check.common_times.length - 1)
    : 0
  const timeSec = check?.common_times[position]

  // 依存配列を「通信に関わる値」だけに絞るため、先にプリミティブとして取り出しておく
  const plane = params?.plane
  const sliceIndex = params?.sliceIndex
  const variable = params?.variable
  const showVectors = view === 'pair' // 差分図には流速を描かないので、取得も省く
  const sectionRequest = useMemo<CompareSectionRequest | null>(
    () =>
      view !== 'timeseries' && checkRequest && timeSec !== undefined && plane && sliceIndex !== undefined && variable
        ? { ...checkRequest, time_sec: timeSec, plane, slice_index: sliceIndex, variable, include_vectors: showVectors }
        : null,
    [view, checkRequest, timeSec, plane, sliceIndex, variable, showVectors],
  )
  const debouncedRequest = useDebounced(sectionRequest, 150)
  const {
    data: section,
    loading: sectionLoading,
    error: sectionError,
  } = useLatestRequest(debouncedRequest, fetchCompareSection)

  // 操作パネルには、いま表示している図のカラーマップを見せる
  const viewParams = useMemo(
    () => (params && view !== 'timeseries' ? { ...params, colormap: colormaps[view] } : params),
    [params, colormaps, view],
  )
  const diffView = useMemo(
    () => (section && viewParams && view === 'diff' ? buildDiffView(section, viewParams, labels) : null),
    [section, viewParams, view, labels],
  )
  const pairViews = useMemo(
    () => (section && viewParams && view === 'pair' ? buildPairViews(section, viewParams, labels) : null),
    [section, viewParams, view, labels],
  )

  function updateParams(patch: Partial<SectionParams>) {
    const { colormap, ...rest } = patch
    if (colormap !== undefined && view !== 'timeseries') setColormaps((prev) => ({ ...prev, [view]: colormap }))
    setParams((prev) => (prev ? { ...prev, ...rest } : prev))
  }

  function handlePlaneChange(next: Plane) {
    if (a) updateParams({ plane: next, sliceIndex: midIndex(sliceAxisSize(a.plt_dims, next)) })
  }

  // ---- 地点時系列 ----
  const [tsParam, setTsParam] = useState('')
  const [tsLocation, setTsLocation] = useState('') // "i,j"
  const [tsParams, setTsParams] = useState<TimeseriesParams | null>(null)

  useEffect(() => {
    if (!check) return
    setTsParam((prev) => (check.common_params.includes(prev) ? prev : (check.common_params[0] ?? '')))
    setTsLocation((prev) =>
      check.common_points.some((p) => `${p.i},${p.j}` === prev)
        ? prev
        : check.common_points[0]
          ? `${check.common_points[0].i},${check.common_points[0].j}`
          : '',
    )
  }, [check])

  const tsRequest = useMemo<CompareTimeseriesRequest | null>(() => {
    if (view !== 'timeseries' || !checkRequest || !tsParam || !tsLocation) return null
    const [i, j] = tsLocation.split(',').map(Number)
    return { ...checkRequest, param: tsParam, i, j }
  }, [view, checkRequest, tsParam, tsLocation])
  const { data: ts, loading: tsLoading, error: tsError } = useLatestRequest(tsRequest, fetchCompareTimeseries)

  // 取り直したら、見た目の設定は残したまま深度の選択だけを新しいデータに合わせる
  const depths = useMemo(() => (ts ? unionDepths(ts) : []), [ts])
  useEffect(() => {
    if (ts) setTsParams((prev) => reconcileTimeseriesParams(prev, depths))
  }, [ts, depths])

  const tsMeta = useMemo(() => ({ depths, variable: ts?.a.variable ?? tsParam }), [depths, ts, tsParam])
  const tsPlotParams = useMemo(
    () =>
      tsParams && ts
        ? {
            ...tsParams,
            axis: {
              ...tsParams.axis,
              title:
                tsParams.axis.title ||
                `${ts.a.variable} 時系列の比較（地点 i=${ts.a.grid.i}, j=${ts.a.grid.j}）: 実線 A=${labels.a} / 破線 B=${labels.b}`,
            },
          }
        : null,
    [tsParams, ts, labels],
  )
  const overlayTraces = useMemo(
    () => (ts && tsParams ? buildOverlayTraces(ts, tsParams, labels) : undefined),
    [ts, tsParams, labels],
  )

  const sectionKey = `compare-${a?.dir_id}-${b?.dir_id}-${plane}-${sliceIndex}-${variable}-${timeSec}`

  return (
    <>
      <div className="time-slider-card point-param-select compare-select">
        <label className="text-field">
          <span>A（基準）</span>
          <select value={a?.dir_id ?? ''} onChange={(e) => setAId(e.target.value)}>
            {runs.map((r) => (
              <option key={r.dir_id} value={r.dir_id}>
                {runLabel(r.root)}
              </option>
            ))}
          </select>
        </label>
        <label className="text-field">
          <span>B（比べる対象）</span>
          <select value={b?.dir_id ?? ''} onChange={(e) => setBId(e.target.value)}>
            {runs.map((r) => (
              <option key={r.dir_id} value={r.dir_id}>
                {runLabel(r.root)}
              </option>
            ))}
          </select>
        </label>
        <div className="segmented compare-view-switch" role="radiogroup" aria-label="比較の表示">
          {VIEWS.map((v) => (
            <label key={v.value} className={`segmented__option ${view === v.value ? 'is-active' : ''}`}>
              <input type="radio" checked={view === v.value} onChange={() => setView(v.value)} />
              {v.label}
            </label>
          ))}
        </div>
      </div>

      {a && b && a.dir_id === b.dir_id && <ErrorBanner message="A と B に別のランを選んでください" />}
      <ErrorBanner message={checkError} />

      {check && viewParams && a && view !== 'timeseries' && (
        <>
          <ErrorBanner message={sectionError} />
          <TimeSlider
            frames={frames}
            position={position}
            onPositionChange={setTimePosition}
            timeUnit={timeUnit}
            onTimeUnitChange={setTimeUnit}
          />
          <div className="section-view__body">
            <SectionControls
              meta={{ variables: check.common_variables }}
              params={viewParams}
              axisSize={sliceAxisSize(a.plt_dims, viewParams.plane)}
              axisCoordLabel={COORD_VAR_LABEL[PLANE_AXIS[viewParams.plane]]}
              onPlaneChange={handlePlaneChange}
              onChange={updateParams}
            />
            {view === 'diff' ? (
              <SectionPlot
                data={diffView?.data ?? null}
                loading={sectionLoading}
                params={diffView?.params ?? viewParams}
                datasetKey={sectionKey}
              />
            ) : (
              // 画面幅が狭いときは横に詰めず縦に並べる（CSS の .compare-pair）
              <div className="compare-pair">
                <SectionPlot
                  data={pairViews?.a.data ?? null}
                  loading={sectionLoading}
                  params={pairViews?.a.params ?? viewParams}
                  datasetKey={`${sectionKey}-a`}
                  compact
                />
                <SectionPlot
                  data={pairViews?.b.data ?? null}
                  loading={sectionLoading}
                  params={pairViews?.b.params ?? viewParams}
                  datasetKey={`${sectionKey}-b`}
                  compact
                />
              </div>
            )}
          </div>
        </>
      )}

      {check && view === 'timeseries' && (
        <>
          <ErrorBanner message={tsError} />
          {check.common_points.length === 0 ? (
            <div className="plot-placeholder compare-hint">
              A と B に同じ格子位置の hist 地点がないため、地点時系列は比較できません
            </div>
          ) : (
            <div className="time-slider-card point-param-select">
              <label className="text-field">
                <span>パラメータ</span>
                <select value={tsParam} onChange={(e) => setTsParam(e.target.value)}>
                  {check.common_params.map((p) => (
                    <option key={p} value={p}>
                      {p}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-field">
                <span>地点（格子位置）</span>
                <select value={tsLocation} onChange={(e) => setTsLocation(e.target.value)}>
                  {check.common_points.map((p) => (
                    <option key={`${p.i},${p.j}`} value={`${p.i},${p.j}`}>
                      i={p.i}, j={p.j}（A: {p.point_a} / B: {p.point_b}）
                    </option>
                  ))}
                </select>
              </label>
            </div>
          )}
          {tsParams && tsPlotParams && (
            <div className="section-view__body">
              <TimeseriesControls
                meta={tsMeta}
                params={tsParams}
                onChange={(patch) => setTsParams((prev) => (prev ? { ...prev, ...patch } : prev))}
              />
              <TimeseriesPlot
                meta={tsMeta}
                data={ts ? ts.a : null}
                loading={tsLoading}
                params={tsPlotParams}
                traces={overlayTraces}
              />
            </div>
          )}
        </>
      )}
    </>
  )
}

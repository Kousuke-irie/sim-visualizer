import { useEffect, useMemo, useState } from 'react'
import TimeSlider from './TimeSlider'
import { buildDiffView, runLabel } from './compareFigure'
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
import { compareCheck, fetchCompareSection } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useLatestRequest } from '../../hooks/useLatestRequest'
import type {
  CompareCheckRequest,
  CompareSectionRequest,
  DirectoryMeta,
  Plane,
  PltFrameMeta,
  SectionParams,
  TimeUnit,
} from '../../types'

type Props = { runs: DirectoryMeta[] }

// 差分は 0 を中心にした発散型のカラーマップで描く（DESIGN_research_features.md §3.3）
const DIFF_COLORMAP = 'RdBu_r'

// ディレクトリモードの「比較」タブ。開いたランから A・B を選び、同じ時刻・同じ断面の B−A を描く
export default function DirectoryComparePanel({ runs }: Props) {
  // 既定は A = 先に開いたラン、B = 後から開いたラン
  const [aId, setAId] = useState(() => runs[runs.length - 2]?.dir_id ?? '')
  const [bId, setBId] = useState(() => runs[runs.length - 1]?.dir_id ?? '')
  // 同じディレクトリを開き直すと dir_id が変わる。選んでいたランが一覧から消えたら既定に戻す
  const a = runs.find((r) => r.dir_id === aId) ?? runs[runs.length - 2]
  const b = runs.find((r) => r.dir_id === bId) ?? runs[runs.length - 1]

  const checkRequest = useMemo<CompareCheckRequest | null>(
    () => (a && b && a.dir_id !== b.dir_id ? { dir_a: a.dir_id, dir_b: b.dir_id } : null),
    [a, b],
  )
  const { data: check, error: checkError } = useLatestRequest(checkRequest, compareCheck)

  const [params, setParams] = useState<SectionParams | null>(null)
  // null の間は中央の時刻を表示する（共通の時刻が分かるまで位置を決められないため）
  const [timePosition, setTimePosition] = useState<number | null>(null)
  const [timeUnit, setTimeUnit] = useState<TimeUnit>('sec')

  // A・B を選び直して共通の変数・時刻が変わったら、それに合わせて初期化する（見た目の設定は残す）
  useEffect(() => {
    if (!check || !a) return
    setParams((prev) => {
      const base = prev ?? {
        ...createDefaultSectionParams(a.plt_dims, check.common_variables, 'YZ'),
        colormap: DIFF_COLORMAP,
      }
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
  const sectionRequest = useMemo<CompareSectionRequest | null>(
    () =>
      checkRequest && timeSec !== undefined && plane && sliceIndex !== undefined && variable
        ? { ...checkRequest, time_sec: timeSec, plane, slice_index: sliceIndex, variable, include_vectors: false }
        : null,
    [checkRequest, timeSec, plane, sliceIndex, variable],
  )
  const debouncedRequest = useDebounced(sectionRequest, 150)
  const { data, loading, error } = useLatestRequest(debouncedRequest, fetchCompareSection)

  const labels = useMemo(() => ({ a: a ? runLabel(a.root) : 'A', b: b ? runLabel(b.root) : 'B' }), [a, b])
  const view = useMemo(() => (data && params ? buildDiffView(data, params, labels) : null), [data, params, labels])

  function updateParams(patch: Partial<SectionParams>) {
    setParams((prev) => (prev ? { ...prev, ...patch } : prev))
  }

  function handlePlaneChange(next: Plane) {
    if (a) updateParams({ plane: next, sliceIndex: midIndex(sliceAxisSize(a.plt_dims, next)) })
  }

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
      </div>

      {a && b && a.dir_id === b.dir_id && <ErrorBanner message="A と B に別のランを選んでください" />}
      <ErrorBanner message={checkError} />
      <ErrorBanner message={error} />

      {check && params && a && (
        <>
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
              params={params}
              axisSize={sliceAxisSize(a.plt_dims, params.plane)}
              axisCoordLabel={COORD_VAR_LABEL[PLANE_AXIS[params.plane]]}
              onPlaneChange={handlePlaneChange}
              onChange={updateParams}
            />
            <SectionPlot
              data={view?.data ?? null}
              loading={loading}
              params={view?.params ?? params}
              datasetKey={`compare-${a.dir_id}-${b?.dir_id}-${plane}-${sliceIndex}-${variable}-${timeSec}`}
            />
          </div>
        </>
      )}
    </>
  )
}

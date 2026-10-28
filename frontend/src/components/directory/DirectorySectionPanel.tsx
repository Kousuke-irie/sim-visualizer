import { useMemo, useState } from 'react'
import TimeSlider from './TimeSlider'
import ErrorBanner from '../common/ErrorBanner'
import SectionControls from '../section/SectionControls'
import SectionPlot from '../section/SectionPlot'
import {
  COORD_VAR_LABEL,
  PLANE_AXIS,
  createDefaultSectionParams,
  midIndex,
  sliceAxisSize,
} from '../section/sectionDefaults'
import { fetchDirectorySectionData } from '../../api/client'
import { useDebounced } from '../../hooks/useDebounced'
import { useLatestRequest } from '../../hooks/useLatestRequest'
import type { DirectoryMeta, DirectorySectionDataRequest, Plane, SectionParams, TimeUnit } from '../../types'

type Props = { meta: DirectoryMeta }

// ディレクトリモードの「空間分布」タブ。時間スライダーで選んだフレームの断面を描く
export default function DirectorySectionPanel({ meta }: Props) {
  const [framePosition, setFramePosition] = useState(() => midIndex(meta.plt_frames.length))
  const [frameTimeUnit, setFrameTimeUnit] = useState<TimeUnit>('sec')
  const [params, setParams] = useState<SectionParams>(() =>
    createDefaultSectionParams(meta.plt_dims, meta.plt_variables, 'YZ'),
  )

  function updateParams(patch: Partial<SectionParams>) {
    setParams((prev) => ({ ...prev, ...patch }))
  }

  function handlePlaneChange(plane: Plane) {
    updateParams({ plane, sliceIndex: midIndex(sliceAxisSize(meta.plt_dims, plane)) })
  }

  const currentFrame = meta.plt_frames[framePosition]

  // データ取得（サーバー往復）が必要なのは平面・スライス位置・変数・フレームが変わったときだけ。
  // 色・レベル数などのスタイル変更は SectionPlot 側でクライアントのみ即時反映される（DESIGN.md 7-1節の方針を踏襲）。
  // 依存配列を「通信に関わる値」だけに絞るため、先にプリミティブとして取り出しておく
  const dirId = meta.dir_id
  const frameIndex = currentFrame?.index
  const { plane, sliceIndex, variable } = params
  const request = useMemo<DirectorySectionDataRequest | null>(
    () =>
      frameIndex === undefined
        ? null
        : { dir_id: dirId, frame_index: frameIndex, plane, slice_index: sliceIndex, variable, include_vectors: true },
    [dirId, frameIndex, plane, sliceIndex, variable],
  )
  const debouncedRequest = useDebounced(request, 150)
  const { data, loading, error } = useLatestRequest(debouncedRequest, fetchDirectorySectionData)

  const datasetKey = `${dirId}-${plane}-${sliceIndex}-${variable}-${frameIndex}`

  return (
    <>
      <ErrorBanner message={error} />
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
          params={params}
          axisSize={sliceAxisSize(meta.plt_dims, plane)}
          axisCoordLabel={COORD_VAR_LABEL[PLANE_AXIS[plane]]}
          onPlaneChange={handlePlaneChange}
          onChange={updateParams}
        />
        <SectionPlot data={data} loading={loading} params={params} datasetKey={datasetKey} />
      </div>
    </>
  )
}

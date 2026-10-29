import { describe, expect, it } from 'vitest'
import type {
  CompareSectionResponse,
  CompareTimeseriesResponse,
  DirectorySectionDataResponse,
  DirectoryTimeseriesResponse,
} from '../../types'
import { createDefaultTimeseriesParams } from '../timeseries/timeseriesParams'
import { createDefaultSectionParams } from '../section/sectionDefaults'
import {
  buildDiffView,
  buildOverlayTraces,
  buildPairViews,
  runLabel,
  symmetricRange,
  unionDepths,
} from './compareFigure'

function section(values: (number | null)[][]): DirectorySectionDataResponse {
  return {
    h_coords: [0, 10],
    v_coords: [-2, -1],
    h_label: 'Y',
    v_label: 'Z',
    values,
    vector_h: [
      [0, 1],
      [1, 0],
    ],
    vector_v: [
      [0, 0],
      [0, 0],
    ],
    vector_h_label: 'V',
    vector_v_label: 'W',
    actual_coord: 150,
    actual_index: 15,
    value_range: [1, 4],
    frame_index: 3,
    time_sec: 10800,
  }
}

const RES: CompareSectionResponse = {
  a: section([
    [1, 2],
    [null, 4],
  ]),
  b: section([
    [1.5, 1],
    [3, 4],
  ]),
  diff: [
    [0.5, -1],
    [null, 0],
  ],
  diff_range: [-1, 0.5],
}
const PARAMS = { ...createDefaultSectionParams({ I: 31, J: 61, K: 21 }, ['TEMP'], 'YZ'), colormap: 'RdBu_r' }
const LABELS = { a: 'mecamamo_202606_v2', b: 'mecamamo_202606_v5' }

describe('symmetricRange', () => {
  it('0 を中心に、絶対値の大きい側に合わせる', () => {
    expect(symmetricRange([-1, 0.5])).toEqual([-1, 1])
    expect(symmetricRange([0, 22])).toEqual([-22, 22])
  })

  it('差が無い・有効な点が無いときは ±1', () => {
    expect(symmetricRange([0, 0])).toEqual([-1, 1])
    expect(symmetricRange(null)).toEqual([-1, 1])
  })
})

describe('buildDiffView', () => {
  it('値は差分、値範囲は実際の差分の範囲、座標は B と同じ', () => {
    const { data } = buildDiffView(RES, PARAMS, LABELS)
    expect(data.values).toEqual(RES.diff)
    expect(data.value_range).toEqual([-1, 0.5])
    expect(data.h_coords).toEqual(RES.b.h_coords)
  })

  it('色範囲は自動なら 0 中心の対称、手動ならその値', () => {
    expect(buildDiffView(RES, PARAMS, LABELS).params.colorRange).toEqual({ auto: false, vmin: -1, vmax: 1 })
    const manual = { ...PARAMS, colorRange: { auto: false, vmin: -0.2, vmax: 0.2 } }
    expect(buildDiffView(RES, manual, LABELS).params.colorRange).toEqual(manual.colorRange)
  })

  it('差分図には流速ベクトルを描かない', () => {
    const { data } = buildDiffView(RES, PARAMS, LABELS)
    expect(data.vector_h).toBeNull()
    expect(data.vector_v).toBeNull()
  })

  it('タイトルが未入力なら、どちらからどちらを引いたかを書く', () => {
    const { params } = buildDiffView(RES, PARAMS, LABELS)
    expect(params.axis.title).toBe('TEMP の差（B − A）: mecamamo_202606_v5 − mecamamo_202606_v2（YZ断面, X = 150.0 m）')
  })

  it('入力したタイトルはそのまま使う', () => {
    const custom = { ...PARAMS, axis: { ...PARAMS.axis, title: 'Kv を変えた影響' } }
    expect(buildDiffView(RES, custom, LABELS).params.axis.title).toBe('Kv を変えた影響')
  })
})

describe('runLabel', () => {
  it('パスの末尾のディレクトリ名', () => {
    expect(runLabel('/data/3次元ラン/mecamamo_202606_v5')).toBe('mecamamo_202606_v5')
    expect(runLabel('/data/sim/')).toBe('sim')
  })
})

describe('buildPairViews', () => {
  it('色範囲が自動なら A・B の値範囲の和集合を両方に使う', () => {
    const res = {
      ...RES,
      a: { ...RES.a, value_range: [1, 4] as [number, number] },
      b: { ...RES.b, value_range: [0.5, 3] as [number, number] },
    }
    const { a, b } = buildPairViews(res, PARAMS, LABELS)
    expect(a.params.colorRange).toEqual({ auto: false, vmin: 0.5, vmax: 4 })
    expect(b.params.colorRange).toEqual(a.params.colorRange)
    expect(a.data).toBe(res.a)
    expect(b.data).toBe(res.b)
  })

  it('手動の色範囲はそのまま', () => {
    const manual = { ...PARAMS, colorRange: { auto: false, vmin: 0, vmax: 10 } }
    expect(buildPairViews(RES, manual, LABELS).a.params.colorRange).toEqual(manual.colorRange)
  })

  it('タイトルでどちらのランかを示す', () => {
    const { a, b } = buildPairViews(RES, PARAMS, LABELS)
    expect(a.params.axis.title).toBe('A: mecamamo_202606_v2 — TEMP')
    expect(b.params.axis.title?.startsWith('B: mecamamo_202606_v5 — ')).toBe(true)
  })
})

function hist(depths: string[], values: number[][]): DirectoryTimeseriesResponse {
  return {
    variable: 'DOX',
    point: '01',
    grid: { i: 2, j: 3, n: 1, h: 4 },
    depths,
    depth_values: depths.map((d) => parseFloat(d)),
    times: [0, 3600],
    values,
  }
}

describe('buildOverlayTraces', () => {
  const ts: CompareTimeseriesResponse = {
    point_a: '01',
    point_b: '02',
    a: hist(
      ['-1.75m', '-0.75m'],
      [
        [1, 2],
        [3, 4],
      ],
    ),
    b: hist(
      ['-0.75m', '0.25m'],
      [
        [5, 6],
        [7, 8],
      ],
    ),
  }
  const params = { ...createDefaultTimeseriesParams(unionDepths(ts)), timeUnit: 'hour' as const }

  it('深度は A の並び＋B にしか無いもの', () => {
    expect(unionDepths(ts)).toEqual(['-1.75m', '-0.75m', '0.25m'])
  })

  it('A は実線・B は破線で、同じ深度は同じ色', () => {
    const traces = buildOverlayTraces(ts, params, LABELS) as {
      name: string
      x: number[]
      y: number[]
      line: { color: string; dash: string }
    }[]
    expect(traces.map((t) => t.name)).toEqual(['A -1.75m', 'A -0.75m', 'B -0.75m', 'B 0.25m'])
    const aMid = traces[1]
    const bMid = traces[2]
    expect(aMid.line).toEqual({ color: bMid.line.color, dash: 'solid' })
    expect(bMid.line.dash).toBe('dash')
    expect(bMid.y).toEqual([5, 7]) // B の -0.75m は B 自身の1列目
    expect(aMid.x).toEqual([0, 1]) // 時間単位 hour
  })

  it('選択していない深度は描かない', () => {
    const traces = buildOverlayTraces(ts, { ...params, selectedDepths: ['0.25m'] }, LABELS) as { name: string }[]
    expect(traces.map((t) => t.name)).toEqual(['B 0.25m'])
  })
})

import { describe, expect, it } from 'vitest'
import type { CompareSectionResponse, DirectorySectionDataResponse } from '../../types'
import { createDefaultSectionParams } from '../section/sectionDefaults'
import { buildDiffView, runLabel, symmetricRange } from './compareFigure'

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

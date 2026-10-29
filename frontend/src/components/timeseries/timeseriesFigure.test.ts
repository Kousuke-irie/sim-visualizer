import { describe, expect, it } from 'vitest'
import { LINE_COLORS } from '../../constants'
import type { TimeseriesDataResponse, TimeseriesParams } from '../../types'
import { createDefaultTimeseriesParams } from './timeseriesParams'
import { buildTimeseriesLayout, buildTimeseriesTraces, resolveRange } from './timeseriesFigure'

const META = { depths: ['-1.75m', '-0.75m', '0.25m'], variable: 'DOX' }
const DATA: TimeseriesDataResponse = {
  times: [0, 3600, 7200],
  values: [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
  ],
}

function params(overrides: Partial<TimeseriesParams> = {}): TimeseriesParams {
  return { ...createDefaultTimeseriesParams(META.depths), ...overrides }
}

type Trace = { name: string; x: number[]; y: number[]; line: { color: string } }

describe('buildTimeseriesTraces', () => {
  it('深度ごとに1本、values の列をその深度の系列にする', () => {
    const traces = buildTimeseriesTraces(META, DATA, params()) as Trace[]
    expect(traces.map((t) => t.name)).toEqual(META.depths)
    expect(traces[1].y).toEqual([2, 5, 8])
  })

  it('時間単位を hour にすると秒を 3600 で割る', () => {
    const [trace] = buildTimeseriesTraces(META, DATA, params({ timeUnit: 'hour' })) as Trace[]
    expect(trace.x).toEqual([0, 1, 2])
  })

  it('選択した深度だけを描き、色は深度の並び順で固定（絞り込んでも同じ深度は同じ色）', () => {
    const traces = buildTimeseriesTraces(META, DATA, params({ selectedDepths: ['0.25m'] })) as Trace[]
    expect(traces).toHaveLength(1)
    expect(traces[0].y).toEqual([3, 6, 9])
    expect(traces[0].line.color).toBe(LINE_COLORS[2])
  })
})

describe('resolveRange', () => {
  it('手動で min・max が揃ったときだけ範囲を固定する', () => {
    expect(resolveRange({ auto: false, min: 0, max: 10 })).toEqual([0, 10])
    expect(resolveRange({ auto: false, min: 0 })).toBeUndefined()
    expect(resolveRange({ auto: true, min: 0, max: 10 })).toBeUndefined()
  })
})

describe('buildTimeseriesLayout', () => {
  it('タイトル・軸ラベルは未入力なら自動生成', () => {
    const layout = buildTimeseriesLayout(META, params({ timeUnit: 'hour' }))
    expect(layout.title).toEqual({ text: 'DOX 時系列（深度別）' })
    expect(layout.xaxis?.title).toEqual({ text: 'time [hour]' })
    expect(layout.yaxis?.title).toEqual({ text: 'DOX' })
  })

  it('入力したタイトル・軸ラベルと軸範囲を使う', () => {
    const layout = buildTimeseriesLayout(
      META,
      params({
        axis: { title: '湾奥の溶存酸素', xlabel: '経過時間', ylabel: 'DO' },
        valueRange: { auto: false, min: 1, max: 5 },
      }),
    )
    expect(layout.title).toEqual({ text: '湾奥の溶存酸素' })
    expect(layout.xaxis?.title).toEqual({ text: '経過時間' })
    expect(layout.yaxis).toMatchObject({ title: { text: 'DO' }, range: [1, 5] })
    expect(layout.xaxis?.range).toBeUndefined()
  })
})

describe('線の色', () => {
  // 以前は色見本用のパレット（2番目が白）を流用しており、2番目の深度の線が白い背景に溶けて見えなかった
  it('白い背景で見える色だけを使う（明るすぎる色を含まない）', () => {
    const luminance = (hex: string) => {
      const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
      return 0.2126 * r + 0.7152 * g + 0.0722 * b
    }
    expect(LINE_COLORS.every((c) => luminance(c) < 0.85)).toBe(true)
  })

  it('2番目の深度の線は白ではない', () => {
    const [, second] = buildTimeseriesTraces(META, DATA, params()) as Trace[]
    expect(second.line.color).not.toBe('#ffffff')
  })
})

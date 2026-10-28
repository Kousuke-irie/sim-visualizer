import { describe, expect, it } from 'vitest'
import type { TimeseriesParams } from '../../types'
import { createDefaultTimeseriesParams, reconcileTimeseriesParams } from './timeseriesParams'

const DEPTHS = ['-1.75m', '-0.75m', '0.25m']

function customized(): TimeseriesParams {
  return {
    selectedDepths: ['-0.75m'],
    timeUnit: 'hour',
    timeRange: { auto: false, min: 0, max: 24 },
    valueRange: { auto: false, min: 1, max: 5 },
    axis: { title: '湾奥の溶存酸素', ylabel: 'DO [mg/L]' },
    exportScale: 3,
  }
}

describe('reconcileTimeseriesParams', () => {
  it('初回は全深度を選択した既定値', () => {
    expect(reconcileTimeseriesParams(null, DEPTHS)).toEqual(createDefaultTimeseriesParams(DEPTHS))
  })

  it('取り直してもタイトル・単位・軸範囲・解像度などの見た目は保持する', () => {
    const next = reconcileTimeseriesParams(customized(), DEPTHS)
    const { selectedDepths: _ignored, ...rest } = next
    const { selectedDepths: _ignored2, ...expected } = customized()
    expect(rest).toEqual(expected)
  })

  it('同じ深度が存在すれば選択も引き継ぐ（順序は新しい深度の並び）', () => {
    const prev = { ...customized(), selectedDepths: ['0.25m', '-1.75m'] }
    expect(reconcileTimeseriesParams(prev, DEPTHS).selectedDepths).toEqual(['-1.75m', '0.25m'])
  })

  it('水深の違う地点で引き継げる深度が無ければ全深度を選ぶ', () => {
    expect(reconcileTimeseriesParams(customized(), ['-3.5m', '-2.5m']).selectedDepths).toEqual(['-3.5m', '-2.5m'])
  })
})

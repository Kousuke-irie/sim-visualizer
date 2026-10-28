import { describe, expect, it } from 'vitest'
import { createDefaultSectionParams, defaultVariable, midIndex, sliceAxisSize } from './sectionDefaults'

const DIMS = { I: 31, J: 61, K: 21 }

describe('sectionDefaults', () => {
  it('座標以外の最初の変数を既定の描画変数にする', () => {
    expect(defaultVariable(['X', 'Y', 'Z', 'U', 'TEMP'])).toBe('U')
    expect(defaultVariable(['X', 'Y', 'Z'])).toBe('X')
  })

  it('断面位置の既定は中央', () => {
    expect(midIndex(31)).toBe(15)
    expect(midIndex(4)).toBe(1)
    expect(midIndex(0)).toBe(0)
  })

  it('断面方向ごとに固定する軸の格子数を返す', () => {
    expect(sliceAxisSize(DIMS, 'YZ')).toBe(31)
    expect(sliceAxisSize(DIMS, 'XZ')).toBe(61)
    expect(sliceAxisSize(DIMS, 'XY')).toBe(21)
  })

  it('既定の表示パラメータ（断面ビューとディレクトリモードで共通）', () => {
    expect(createDefaultSectionParams(DIMS, ['X', 'Y', 'Z', 'TEMP'], 'YZ')).toEqual({
      plane: 'YZ',
      sliceIndex: 15,
      variable: 'TEMP',
      colormap: 'viridis',
      customColormap: { enabled: false, low: '#1b4965', useMid: false, mid: '#2a9d8f', high: '#e76f51' },
      fillLevels: 30,
      lineLevels: 10,
      showContourLines: true,
      colorRange: { auto: true },
      vectors: { show: true, skip: 2, width: 1.5, headWidth: 8 },
      axis: { zlim: { auto: true }, aspect: { auto: true, ratio: 1 } },
      exportScale: 2,
    })
  })
})

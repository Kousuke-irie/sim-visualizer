import { describe, expect, it } from 'vitest'
import type { SectionDataResponse, SectionParams } from '../../types'
import {
  ASPECT_MAX,
  ASPECT_MIN,
  buildColorscale,
  buildVectorTraces,
  computeAspectRatio,
  computeAutoZRange,
  computeColorRange,
  computeVRange,
  defaultTitle,
} from './sectionFigure'

function makeParams(overrides: Partial<SectionParams> = {}): SectionParams {
  return {
    plane: 'XZ',
    sliceIndex: 0,
    variable: 'TEMP',
    colormap: 'viridis',
    customColormap: { enabled: false, low: '#000000', useMid: false, mid: '#888888', high: '#ffffff' },
    fillLevels: 30,
    lineLevels: 10,
    showContourLines: true,
    colorRange: { auto: true },
    vectors: { show: true, skip: 1, width: 1.5, headWidth: 8 },
    axis: { zlim: { auto: true }, aspect: { auto: true, ratio: 1 } },
    exportScale: 2,
    ...overrides,
  }
}

// 横 0〜100m、縦 -10〜0m の XZ 断面。最下層の行は全て欠損（海底より下）
function makeData(overrides: Partial<SectionDataResponse> = {}): SectionDataResponse {
  return {
    h_coords: [0, 50, 100],
    v_coords: [-10, -5, 0],
    h_label: 'X',
    v_label: 'Z',
    values: [
      [null, null, null],
      [1, 2, 3],
      [4, 5, 6],
    ],
    vector_h: [
      [null, null, null],
      [1, 0, null],
      [0, 2, 0],
    ],
    vector_v: [
      [null, null, null],
      [0, 1, 0],
      [0, 0, 0],
    ],
    vector_h_label: 'U',
    vector_v_label: 'W',
    actual_coord: 25,
    actual_index: 2,
    value_range: [1, 6],
    ...overrides,
  }
}

describe('buildColorscale', () => {
  it('プリセットの色を 0〜1 に等間隔で配置する', () => {
    const scale = buildColorscale(makeParams({ colormap: 'viridis' }))
    expect(scale[0][0]).toBe(0)
    expect(scale[scale.length - 1][0]).toBe(1)
    const steps = scale.slice(1).map(([pos], i) => pos - scale[i][0])
    steps.forEach((s) => expect(s).toBeCloseTo(steps[0]))
  })

  it('未知のプリセット名は viridis にフォールバックする', () => {
    expect(buildColorscale(makeParams({ colormap: 'no-such-map' }))).toEqual(
      buildColorscale(makeParams({ colormap: 'viridis' })),
    )
  })

  it('カスタム2色・3色', () => {
    const custom = { enabled: true, low: '#111111', useMid: false, mid: '#222222', high: '#333333' }
    expect(buildColorscale(makeParams({ customColormap: custom }))).toEqual([
      [0, '#111111'],
      [1, '#333333'],
    ])
    expect(buildColorscale(makeParams({ customColormap: { ...custom, useMid: true } }))).toEqual([
      [0, '#111111'],
      [0.5, '#222222'],
      [1, '#333333'],
    ])
  })
})

describe('computeColorRange', () => {
  it('自動ならデータの値範囲', () => {
    expect(computeColorRange(makeData(), makeParams())).toEqual([1, 6])
  })

  it('手動なら指定値', () => {
    expect(computeColorRange(makeData(), makeParams({ colorRange: { auto: false, vmin: 0, vmax: 10 } }))).toEqual([
      0, 10,
    ])
  })

  it('手動でも値が欠けていれば自動にフォールバック', () => {
    expect(computeColorRange(makeData(), makeParams({ colorRange: { auto: false, vmin: 0 } }))).toEqual([1, 6])
  })
})

describe('縦軸レンジ', () => {
  it('全欠損の行（海底より下）を除いた範囲にし、上端は水面 0 を含める', () => {
    expect(computeAutoZRange(makeData())).toEqual([-5, 0])
    expect(computeAutoZRange(makeData({ v_coords: [-10, -5, -2] }))).toEqual([-5, 0])
  })

  it('全行が欠損なら座標全体', () => {
    const empty = makeData({ values: [[null], [null], [null]], h_coords: [0] })
    expect(computeAutoZRange(empty)).toEqual([-10, 0])
  })

  it('縦軸が Z でない（XY 断面）なら undefined で Plotly に任せる', () => {
    expect(computeVRange(makeData({ v_label: 'Y' }), makeParams())).toBeUndefined()
  })

  it('zlim 手動指定を優先する', () => {
    const params = makeParams({ axis: { zlim: { auto: false, min: -8, max: -1 }, aspect: { auto: true } } })
    expect(computeVRange(makeData(), params)).toEqual([-8, -1])
  })
})

describe('computeAspectRatio（Plotly の scaleratio への変換）', () => {
  // scaleratio = 望む見た目の縦横比 / データの縦横比。一度この変換を取り違えたことがあるため回帰テストで固定する
  it('手動指定の縦横比が画面上でそのまま実現される', () => {
    const data = makeData()
    const params = makeParams({ axis: { zlim: { auto: true }, aspect: { auto: false, ratio: 0.5 } } })
    const vRange: [number, number] = [-10, 0]
    const rawAspect = 10 / 100
    const scaleratio = computeAspectRatio(data, params, vRange)
    expect(rawAspect * scaleratio).toBeCloseTo(0.5)
  })

  it('自動では極端に潰れた断面を下限 ASPECT_MIN にクランプする', () => {
    const data = makeData()
    const vRange: [number, number] = [-10, 0] // rawAspect = 0.1 < 1/3
    expect((10 / 100) * computeAspectRatio(data, makeParams(), vRange)).toBeCloseTo(ASPECT_MIN)
  })

  it('自動では極端に縦長の断面を上限 ASPECT_MAX にクランプする', () => {
    const data = makeData({ h_coords: [0, 1] })
    const vRange: [number, number] = [-10, 0] // rawAspect = 10
    expect(10 * computeAspectRatio(data, makeParams(), vRange)).toBeCloseTo(ASPECT_MAX)
  })

  it('範囲内ならデータ本来の比率のまま（scaleratio = 1）', () => {
    const data = makeData({ h_coords: [0, 10] })
    expect(computeAspectRatio(data, makeParams(), [-10, 0])).toBeCloseTo(1)
  })
})

describe('buildVectorTraces', () => {
  it('非表示やベクトル無しなら null', () => {
    expect(buildVectorTraces(makeData(), makeParams({ vectors: { show: false, skip: 1, width: 1, headWidth: 8 } }), 100)).toBeNull()
    expect(buildVectorTraces(makeData({ vector_h: null, vector_v: null }), makeParams(), 100)).toBeNull()
  })

  it('欠損点を除き、矢軸を [始点, 終点, null] の区切りで1トレースにまとめる', () => {
    const result = buildVectorTraces(makeData(), makeParams(), 100)!
    const [shaft, head] = result.traces as { x: (number | null)[]; y: (number | null)[] }[]
    // 有効な点: (1行目) 2点、(2行目) 3点 = 5点
    expect(shaft.x).toHaveLength(5 * 3)
    expect(head.x).toHaveLength(5)
    expect(shaft.x.filter((_, i) => i % 3 === 2).every((v) => v === null)).toBe(true)
    expect(result.maxMag).toBeCloseTo(2)
  })

  it('スケール自動では最大流速の矢印が横幅の 8% になる', () => {
    const result = buildVectorTraces(makeData(), makeParams(), 100)!
    const shaft = result.traces[0] as { x: number[] }
    const lengths = []
    for (let i = 0; i < shaft.x.length; i += 3) lengths.push(Math.abs(shaft.x[i + 1] - shaft.x[i]))
    expect(Math.max(...lengths)).toBeCloseTo(8)
  })

  it('間引き skip=2 で 1 つおきの格子点だけ使う', () => {
    const params = makeParams({ vectors: { show: true, skip: 2, width: 1, headWidth: 8 } })
    const result = buildVectorTraces(makeData(), params, 100)!
    // 行 0,2 × 列 0,2 のうち有効なのは (2,0),(2,2) の 2点
    expect((result.traces[1] as { x: number[] }).x).toEqual([0, 100])
  })

  it('矢先の角度は「上向き三角」基準で流向に回転させる', () => {
    const data = makeData({
      vector_h: [[null], [null], [1]],
      vector_v: [[null], [null], [0]],
      h_coords: [0],
    })
    const head = buildVectorTraces(data, makeParams(), 100)!.traces[1] as { marker: { angle: number[] } }
    expect(head.marker.angle[0]).toBeCloseTo(90) // 右向きの流れ = 時計回りに 90°
  })
})

describe('defaultTitle', () => {
  it('変数・断面方向・断面位置を含む', () => {
    expect(defaultTitle(makeParams({ plane: 'XZ' }), makeData())).toBe('TEMP 分布（XZ断面, Y = 25.0 m）')
  })
})

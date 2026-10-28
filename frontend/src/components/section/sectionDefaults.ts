// 断面ビューとディレクトリモードで共通の既定値。以前は両方のコンポーネントに同じ定義が書き写されていた。
import type { Dims, Plane, SectionParams } from '../../types'

// 断面方向ごとに固定する格子軸と、その軸に対応する座標変数
export const PLANE_AXIS: Record<Plane, keyof Dims> = { YZ: 'I', XZ: 'J', XY: 'K' }
export const COORD_VAR_LABEL: Record<keyof Dims, string> = { I: 'X', J: 'Y', K: 'Z' }

export function defaultVariable(variables: string[]): string {
  return variables.find((v) => !['X', 'Y', 'Z'].includes(v)) ?? variables[0]
}

export function midIndex(size: number): number {
  return Math.max(0, Math.floor((size - 1) / 2))
}

export function sliceAxisSize(dims: Dims, plane: Plane): number {
  return dims[PLANE_AXIS[plane]]
}

export function createDefaultSectionParams(dims: Dims, variables: string[], plane: Plane): SectionParams {
  return {
    plane,
    sliceIndex: midIndex(sliceAxisSize(dims, plane)),
    variable: defaultVariable(variables),
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

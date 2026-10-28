// 断面図の Plotly 図形を組み立てる純粋関数群。
// React やネットワークに依存しないため、単体テスト（sectionFigure.test.ts）で直接検証する。
import type { Data } from 'plotly.js'
import { COLORMAP_STOPS } from '../../constants'
import type { Plane, SectionDataResponse, SectionParams } from '../../types'

export const ASPECT_MIN = 1 / 3
export const ASPECT_MAX = 3

export const SLICE_COORD_LABEL: Record<Plane, string> = { YZ: 'X', XZ: 'Y', XY: 'Z' }

export function clamp(value: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, value))
}

export function buildColorscale(params: SectionParams): [number, string][] {
  if (params.customColormap.enabled) {
    const { low, useMid, mid, high } = params.customColormap
    return useMid
      ? [
          [0, low],
          [0.5, mid],
          [1, high],
        ]
      : [
          [0, low],
          [1, high],
        ]
  }
  const stops = COLORMAP_STOPS[params.colormap] ?? COLORMAP_STOPS.viridis
  const n = stops.length - 1
  return stops.map((color, i) => [i / n, color])
}

export function computeColorRange(data: SectionDataResponse, params: SectionParams): [number, number] {
  if (!params.colorRange.auto && params.colorRange.vmin != null && params.colorRange.vmax != null) {
    return [params.colorRange.vmin, params.colorRange.vmax]
  }
  return data.value_range
}

export function computeAutoZRange(data: SectionDataResponse): [number, number] {
  let lo = Infinity
  let hi = -Infinity
  data.values.forEach((row, i) => {
    if (row.some((v) => v !== null)) {
      lo = Math.min(lo, data.v_coords[i])
      hi = Math.max(hi, data.v_coords[i])
    }
  })
  if (!Number.isFinite(lo)) {
    return [Math.min(...data.v_coords), Math.max(...data.v_coords)]
  }
  return [lo, Math.max(0, hi)]
}

export function computeVRange(data: SectionDataResponse, params: SectionParams): [number, number] | undefined {
  if (data.v_label !== 'Z') return undefined
  if (!params.axis.zlim.auto && params.axis.zlim.min != null && params.axis.zlim.max != null) {
    return [params.axis.zlim.min, params.axis.zlim.max]
  }
  return computeAutoZRange(data)
}

// Plotly の yaxis.scaleratio は「x軸の単位あたりピクセル数」に対する倍率であり、
// 画面上に実際に表示される縦横比（desiredAspect）そのものではない。
// desiredAspect = rawAspect(データの縦横比) * scaleratio という関係になるため、
// scaleratio = desiredAspect / rawAspect を返す必要がある。
export function computeAspectRatio(data: SectionDataResponse, params: SectionParams, vRange?: [number, number]): number {
  const hExtent = Math.max(...data.h_coords) - Math.min(...data.h_coords) || 1
  const [vLo, vHi] = vRange ?? [Math.min(...data.v_coords), Math.max(...data.v_coords)]
  const vExtent = Math.max(vHi - vLo, 1e-6)
  const rawAspect = vExtent / hExtent

  const desiredAspect = params.axis.aspect.auto
    ? clamp(rawAspect, ASPECT_MIN, ASPECT_MAX)
    : params.axis.aspect.ratio && params.axis.aspect.ratio > 0
      ? params.axis.aspect.ratio
      : 1

  return desiredAspect / rawAspect
}

export function buildVectorTraces(
  data: SectionDataResponse,
  params: SectionParams,
  hExtent: number,
): { traces: Data[]; maxMag: number } | null {
  if (!params.vectors.show || !data.vector_h || !data.vector_v) return null

  const skip = Math.max(1, params.vectors.skip)
  const points: { h: number; v: number; u: number; w: number }[] = []
  for (let i = 0; i < data.v_coords.length; i += skip) {
    const rowU = data.vector_h[i]
    const rowW = data.vector_v[i]
    if (!rowU || !rowW) continue
    for (let j = 0; j < data.h_coords.length; j += skip) {
      const u = rowU[j]
      const w = rowW[j]
      if (u == null || w == null) continue
      points.push({ h: data.h_coords[j], v: data.v_coords[i], u, w })
    }
  }
  if (points.length === 0) return null

  const maxMag = points.reduce((m, p) => Math.max(m, Math.hypot(p.u, p.w)), 0)
  const lengthPerUnit =
    params.vectors.scale && params.vectors.scale > 0
      ? params.vectors.scale
      : maxMag > 0
        ? (0.08 * hExtent) / maxMag
        : 1

  const shaftX: (number | null)[] = []
  const shaftY: (number | null)[] = []
  const headX: number[] = []
  const headY: number[] = []
  const headAngle: number[] = []

  for (const p of points) {
    const tipH = p.h + p.u * lengthPerUnit
    const tipV = p.v + p.w * lengthPerUnit
    shaftX.push(p.h, tipH, null)
    shaftY.push(p.v, tipV, null)
    headX.push(tipH)
    headY.push(tipV)
    headAngle.push((Math.atan2(p.u, p.w) * 180) / Math.PI)
  }

  const shaftTrace: Data = {
    x: shaftX,
    y: shaftY,
    type: 'scatter',
    mode: 'lines',
    line: { color: 'black', width: params.vectors.width },
    hoverinfo: 'skip',
    showlegend: false,
  }
  const headTrace = {
    x: headX,
    y: headY,
    type: 'scatter',
    mode: 'markers',
    marker: { symbol: 'triangle-up', size: params.vectors.headWidth, angle: headAngle, color: 'black' },
    hoverinfo: 'skip',
    showlegend: false,
  } as unknown as Data

  return { traces: [shaftTrace, headTrace], maxMag }
}

export function defaultTitle(params: SectionParams, data: SectionDataResponse): string {
  return `${params.variable} 分布（${params.plane}断面, ${SLICE_COORD_LABEL[params.plane]} = ${data.actual_coord.toFixed(1)} m）`
}

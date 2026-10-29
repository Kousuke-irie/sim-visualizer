// 2ケース比較の「差分（B−A）」表示を、既存の断面図（SectionPlot）で描ける形に組み立てる純粋関数。
// 差分そのものはサーバーで計算済み。ここで決めるのは見た目（0 を中心にした対称な色範囲・タイトル）だけ。
import type { CompareSectionResponse, SectionDataResponse, SectionParams } from '../../types'
import { SLICE_COORD_LABEL } from '../section/sectionFigure'

export type RunLabels = { a: string; b: string }

// 計算結果ディレクトリのパスから、画面に出す短い名前（末尾のディレクトリ名）を取る
export function runLabel(root: string): string {
  const parts = root.split('/').filter(Boolean)
  return parts[parts.length - 1] ?? root
}

// 差分の色範囲は 0 を中心に対称にする（赤=B が大きい、青=B が小さい、を一目で読めるように）。
// 差が全く無いときは範囲が潰れるので ±1 にして、全面が中央色で描かれるようにする
export function symmetricRange(range: [number, number] | null): [number, number] {
  if (!range) return [-1, 1]
  const m = Math.max(Math.abs(range[0]), Math.abs(range[1]))
  return m > 0 ? [-m, m] : [-1, 1]
}

export function diffTitle(res: CompareSectionResponse, params: SectionParams, labels: RunLabels): string {
  const coord = `${SLICE_COORD_LABEL[params.plane]} = ${res.a.actual_coord.toFixed(1)} m`
  return `${params.variable} の差（B − A）: ${labels.b} − ${labels.a}（${params.plane}断面, ${coord}）`
}

export function buildDiffView(
  res: CompareSectionResponse,
  params: SectionParams,
  labels: RunLabels,
): { data: SectionDataResponse; params: SectionParams } {
  const data: SectionDataResponse = {
    ...res.b,
    values: res.diff,
    // 値範囲は実際の差分の範囲（画面の「値範囲」表示に使う）。色だけを対称にするのは下の colorRange で行う
    value_range: res.diff_range ?? [0, 0],
    // 流速の差の矢印は読み取りにくいので、差分図には描かない
    vector_h: null,
    vector_v: null,
    vector_h_label: null,
    vector_v_label: null,
  }
  const [vmin, vmax] = symmetricRange(res.diff_range)
  return {
    data,
    params: {
      ...params,
      // 色範囲が「自動」のときだけ 0 中心の対称にする。手動で指定した範囲は尊重する
      colorRange: params.colorRange.auto ? { auto: false, vmin, vmax } : params.colorRange,
      axis: { ...params.axis, title: params.axis.title || diffTitle(res, params, labels) },
    },
  }
}

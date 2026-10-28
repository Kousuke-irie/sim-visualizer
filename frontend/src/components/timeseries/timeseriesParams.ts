import type { TimeseriesParams } from '../../types'

export function createDefaultTimeseriesParams(depths: string[]): TimeseriesParams {
  return {
    selectedDepths: [...depths],
    timeUnit: 'sec',
    timeRange: { auto: true },
    valueRange: { auto: true },
    axis: {},
    exportScale: 2,
  }
}

// 地点・パラメータを切り替えてデータを取り直したときの表示設定の引き継ぎ。
// タイトルや軸範囲などユーザーが決めた見た目は残し、データに依存する深度の選択だけを新しい深度に合わせる。
// 深度ラベルは地点の水深で変わるため、引き継げる深度が1つも無ければ全深度を表示する。
export function reconcileTimeseriesParams(prev: TimeseriesParams | null, depths: string[]): TimeseriesParams {
  if (!prev) return createDefaultTimeseriesParams(depths)
  const kept = depths.filter((d) => prev.selectedDepths.includes(d))
  return { ...prev, selectedDepths: kept.length > 0 ? kept : [...depths] }
}

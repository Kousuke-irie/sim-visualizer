// 時系列グラフの線の色（深度ごと）。白い背景で見分けやすい Tableau 10。
// COLOR_PALETTE は色を選ぶ見本用で白や黒を含むため、線には使わない（白い線は背景に溶けて見えなくなる）
export const LINE_COLORS = [
  '#4e79a7', // 青
  '#f28e2b', // 橙
  '#e15759', // 赤
  '#76b7b2', // 青緑
  '#59a14f', // 緑
  '#edc948', // 黄
  '#b07aa1', // 紫
  '#ff9da7', // ピンク
  '#9c755f', // 茶
  '#bab0ac', // グレー
]

// カスタムカラーマップで色を選ぶときの見本（ColorSwatchPicker）
export const COLOR_PALETTE = [
  '#000000', // 黒
  '#ffffff', // 白
  '#9ca3af', // グレー
  '#14213d', // 紺
  '#2563eb', // 青
  '#38bdf8', // 水色
  '#14b8a6', // 青緑
  '#22c55e', // 緑
  '#84cc16', // 黄緑
  '#eab308', // 黄
  '#f97316', // 橙
  '#ef4444', // 赤
  '#ec4899', // ピンク
  '#8b5cf6', // 紫
  '#92400e', // 茶
]

// matplotlib の代表的なカラーマップの色味を近似したストップ配列。
// プリセット選択ドロップダウンのプレビューと、Plotly の実際の colorscale
// 生成の両方で共用する。
export const COLORMAP_STOPS: Record<string, string[]> = {
  viridis: ['#440154', '#3b528b', '#21908d', '#5dc963', '#fde725'],
  plasma: ['#0d0887', '#7e03a8', '#cc4778', '#f89441', '#f0f921'],
  inferno: ['#000004', '#420a68', '#932667', '#dd513a', '#fca50a', '#fcffa4'],
  magma: ['#000004', '#3b0f70', '#8c2981', '#de4968', '#fe9f6d', '#fcfdbf'],
  cividis: ['#00204d', '#414d6b', '#7c7b78', '#b9ac70', '#ffe945'],
  coolwarm: ['#3b4cc0', '#7396f5', '#dddddd', '#f6a385', '#b40426'],
  jet: ['#000080', '#0000ff', '#00ffff', '#ffff00', '#ff0000', '#800000'],
  RdBu_r: ['#2166ac', '#67a9cf', '#f7f7f7', '#ef8a62', '#b2182b'],
}

export const COLORMAP_NAMES = Object.keys(COLORMAP_STOPS)

export const COLORMAP_GRADIENTS: Record<string, string> = Object.fromEntries(
  Object.entries(COLORMAP_STOPS).map(([name, stops]) => [name, `linear-gradient(to right, ${stops.join(', ')})`]),
)

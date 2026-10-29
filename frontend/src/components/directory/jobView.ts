import type { Job, JobStatus } from '../../types'

// 計算の待ち行列の表示（DESIGN_research_features.md §4.1 の 5・6）。React に依存しない純粋関数

export const STATUS_LABEL: Record<JobStatus, string> = {
  queued: '順番待ち',
  compiling: 'コンパイル中',
  running: '計算中',
  succeeded: '完了',
  failed: '失敗',
  cancelled: '中止',
  interrupted: '中断',
}

const ACTIVE: ReadonlySet<JobStatus> = new Set(['queued', 'compiling', 'running'])

export function isActive(job: Job): boolean {
  return ACTIVE.has(job.status)
}

// 終わっていない計算があるあいだだけ、一覧を取り直す
export function hasActiveJobs(jobs: readonly Job[]): boolean {
  return jobs.some(isActive)
}

// 結果を開けるのは、出力が1枚以上あり、もう書き換わらないもの（中止・中断でも途中までは見られる）
export function canOpenResult(job: Job): boolean {
  return !isActive(job) && job.frames_done > 0
}

export function progressRatio(job: Job): number {
  if (job.frames_expected <= 0) return 0
  return Math.min(1, job.frames_done / job.frames_expected)
}

// 7時間の計算を想定し、時間・分まで。1分未満だけ秒で出す
export function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined || !Number.isFinite(seconds)) return '—'
  const s = Math.max(0, Math.round(seconds))
  if (s < 60) return `${s}秒`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return h > 0 ? `${h}時間${m}分` : `${m}分`
}

export function etaText(job: Job): string | null {
  if (job.status !== 'running') return null
  if (job.eta_sec === null) return '終了予定は、2枚目の出力が出たら分かります'
  return `終了まで約 ${formatDuration(job.eta_sec)}`
}

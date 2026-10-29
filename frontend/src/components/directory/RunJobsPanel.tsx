import { useCallback, useEffect, useState } from 'react'
import { STATUS_LABEL, canOpenResult, etaText, formatDuration, hasActiveJobs, isActive, progressRatio } from './jobView'
import { runLabel } from './compareFigure'
import ErrorBanner from '../common/ErrorBanner'
import { cancelJob, fetchJobLog, listJobs } from '../../api/client'
import type { Job } from '../../types'

// 7時間の計算の進み具合を見るには数秒おきで十分。runner への問い合わせを増やしすぎない
export const POLL_MS = 3000
const LOG_LINES = 40

type Props = {
  // 増えるたびに一覧を取り直す（新しい計算を待ち行列に入れた直後など）
  refreshKey: number
  onOpenRun: (path: string) => void
  onCompare: (basePath: string, newPath: string) => void
}

// 計算の待ち行列（DESIGN_research_features.md §4.1 の 5・6）。runner が保存している状態を表示し、中止・結果の表示ができる
export default function RunJobsPanel({ refreshKey, onOpenRun, onCompare }: Props) {
  const [jobs, setJobs] = useState<Job[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    try {
      setJobs((await listJobs()).jobs)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : '計算の一覧を取得できませんでした')
    }
  }, [])

  useEffect(() => {
    void reload()
  }, [reload, refreshKey])

  // 終わっていない計算があるあいだだけ取り直す（終わったあとも問い合わせ続けない）
  const active = jobs !== null && hasActiveJobs(jobs)
  useEffect(() => {
    if (!active) return
    const timer = setInterval(() => void reload(), POLL_MS)
    return () => clearInterval(timer)
  }, [active, reload])

  async function handleCancel(job: Job) {
    if (!window.confirm(`${job.name} の計算を中止しますか？（途中までの出力は残ります）`)) return
    try {
      await cancelJob(job.job_id)
    } catch (err) {
      setError(err instanceof Error ? err.message : '中止できませんでした')
    }
    await reload()
  }

  return (
    <section className="time-slider-card new-run__section" aria-label="計算の待ち行列">
      <h3>計算の待ち行列（1本ずつ順に、コンパイル → 実行）</h3>
      <ErrorBanner message={error} onDismiss={() => setError(null)} />
      {jobs !== null && jobs.length === 0 && <p className="new-run__note">まだ計算はありません</p>}
      <ul className="jobs">
        {jobs?.map((job) => (
          <li key={job.job_id} className={`jobs__item jobs__item--${job.status}`} data-run-dir={job.run_dir}>
            <div className="jobs__head">
              <strong>{job.name}</strong>
              <span className={`chip jobs__status jobs__status--${job.status}`}>{STATUS_LABEL[job.status]}</span>
              <span className="jobs__frames">
                出力 {job.frames_done} / {job.frames_expected} フレーム
              </span>
              <span className="jobs__time">経過 {formatDuration(job.elapsed_sec)}</span>
              {etaText(job) && <span className="jobs__time">{etaText(job)}</span>}
            </div>
            <progress className="jobs__progress" value={progressRatio(job)} max={1} aria-label={`${job.name} の進捗`} />
            {job.message && <p className="new-run__note">{job.message}</p>}
            <div className="jobs__actions">
              {isActive(job) && (
                <button type="button" className="btn-secondary" onClick={() => handleCancel(job)}>
                  中止
                </button>
              )}
              {canOpenResult(job) && (
                <>
                  <button type="button" className="btn-primary" onClick={() => onOpenRun(job.run_dir)}>
                    開く
                  </button>
                  {job.base_run && (
                    <button
                      type="button"
                      className="btn-secondary"
                      title={`${runLabel(job.base_run)}（A）と ${job.name}（B）を比べます`}
                      onClick={() => onCompare(job.base_run, job.run_dir)}
                    >
                      元のランと比較
                    </button>
                  )}
                </>
              )}
            </div>
            <JobLogView job={job} />
          </li>
        ))}
      </ul>
    </section>
  )
}

// ログの末尾。開いたときだけ取りにいき、計算中は一覧と同じ間隔で取り直す
function JobLogView({ job }: { job: Job }) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const running = isActive(job)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    const load = async () => {
      try {
        const log = await fetchJobLog(job.job_id, LOG_LINES)
        if (cancelled) return
        setText(log.text)
        setError(null)
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : 'ログを取得できませんでした')
      }
    }
    void load()
    const timer = running ? setInterval(load, POLL_MS) : undefined
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [open, running, job.job_id])

  return (
    <details className="jobs__log" onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary>ログの末尾（simviz_run.log）</summary>
      <ErrorBanner message={error} />
      <pre>{text === null ? '読み込んでいます…' : text || '（まだ出力はありません）'}</pre>
    </details>
  )
}

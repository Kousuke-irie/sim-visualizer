import { describe, expect, it } from 'vitest'
import type { Job } from '../../types'
import { canOpenResult, etaText, formatDuration, hasActiveJobs, progressRatio } from './jobView'

function makeJob(patch: Partial<Job> = {}): Job {
  return {
    job_id: 'j1',
    name: 'case_v2',
    run_dir: '/data/runs/case_v2',
    base_run: '/data/runs/case_v1',
    status: 'running',
    message: '',
    created_at: '2026-10-29T00:00:00+00:00',
    started_at: '2026-10-29T00:00:00+00:00',
    finished_at: null,
    exit_code: null,
    frames_done: 2,
    frames_expected: 8,
    elapsed_sec: 60,
    eta_sec: 360,
    ...patch,
  }
}

describe('formatDuration', () => {
  it('1分未満は秒、それ以上は分・時間で出す', () => {
    expect(formatDuration(42.4)).toBe('42秒')
    expect(formatDuration(125)).toBe('2分')
    expect(formatDuration(7 * 3600 + 5 * 60)).toBe('7時間5分')
  })

  it('不明な値は — にする', () => {
    expect(formatDuration(null)).toBe('—')
    expect(formatDuration(undefined)).toBe('—')
  })
})

describe('進捗', () => {
  it('書き出したフレーム数の比で、1 を超えない', () => {
    expect(progressRatio(makeJob({ frames_done: 2, frames_expected: 8 }))).toBe(0.25)
    expect(progressRatio(makeJob({ frames_done: 9, frames_expected: 8 }))).toBe(1)
    expect(progressRatio(makeJob({ frames_expected: 0 }))).toBe(0)
  })

  it('終了予定は計算中だけ出し、見込みが立つまではその旨を出す', () => {
    expect(etaText(makeJob())).toBe('終了まで約 6分')
    expect(etaText(makeJob({ eta_sec: null }))).toMatch(/2枚目/)
    expect(etaText(makeJob({ status: 'succeeded' }))).toBeNull()
  })
})

describe('一覧の取り直しと結果の表示', () => {
  it('終わっていない計算があるあいだだけ取り直す', () => {
    expect(hasActiveJobs([makeJob({ status: 'succeeded' }), makeJob({ status: 'queued' })])).toBe(true)
    expect(hasActiveJobs([makeJob({ status: 'failed' }), makeJob({ status: 'interrupted' })])).toBe(false)
  })

  it('結果を開けるのは、終わっていて出力が1枚以上あるもの', () => {
    expect(canOpenResult(makeJob({ status: 'succeeded', frames_done: 8 }))).toBe(true)
    expect(canOpenResult(makeJob({ status: 'cancelled', frames_done: 3 }))).toBe(true)
    expect(canOpenResult(makeJob({ status: 'running', frames_done: 3 }))).toBe(false)
    expect(canOpenResult(makeJob({ status: 'failed', frames_done: 0 }))).toBe(false)
  })
})

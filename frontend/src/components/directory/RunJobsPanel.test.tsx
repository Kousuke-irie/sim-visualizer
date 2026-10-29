// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import RunJobsPanel, { POLL_MS } from './RunJobsPanel'
import { cancelJob, listJobs } from '../../api/client'
import type { Job } from '../../types'

vi.mock('../../api/client', () => ({
  listJobs: vi.fn(),
  cancelJob: vi.fn(),
  fetchJobLog: vi.fn(async () => ({ job_id: 'j1', text: '', truncated: false })),
}))

function job(patch: Partial<Job>): Job {
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

const mockedList = vi.mocked(listJobs)

beforeEach(() => {
  vi.useFakeTimers()
  mockedList.mockReset()
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
})

async function renderPanel(props: Partial<Parameters<typeof RunJobsPanel>[0]> = {}) {
  render(<RunJobsPanel refreshKey={0} onOpenRun={() => {}} onCompare={() => {}} {...props} />)
  await act(async () => {}) // 最初の一覧の取得を待つ
}

describe('RunJobsPanel', () => {
  it('計算中は進み具合と中止ボタンを出し、結果を開くボタンは出さない', async () => {
    mockedList.mockResolvedValue({ jobs: [job({})] })
    await renderPanel()
    expect(screen.getByText('計算中')).toBeTruthy()
    expect(screen.getByText('出力 2 / 8 フレーム')).toBeTruthy()
    expect(screen.getByText('終了まで約 6分')).toBeTruthy()
    expect(screen.getByRole('button', { name: '中止' })).toBeTruthy()
    expect(screen.queryByRole('button', { name: '開く' })).toBeNull()
  })

  it('終わった計算は、開く・元のランと比較できる', async () => {
    mockedList.mockResolvedValue({ jobs: [job({ status: 'succeeded', frames_done: 8, eta_sec: null })] })
    const onCompare = vi.fn()
    const onOpenRun = vi.fn()
    await renderPanel({ onCompare, onOpenRun })
    fireEvent.click(screen.getByRole('button', { name: '元のランと比較' }))
    expect(onCompare).toHaveBeenCalledWith('/data/runs/case_v1', '/data/runs/case_v2')
    fireEvent.click(screen.getByRole('button', { name: '開く' }))
    expect(onOpenRun).toHaveBeenCalledWith('/data/runs/case_v2')
    expect(screen.queryByRole('button', { name: '中止' })).toBeNull()
  })

  it('終わっていない計算があるあいだだけ一覧を取り直し、終わったら止める', async () => {
    mockedList
      .mockResolvedValueOnce({ jobs: [job({ status: 'running' })] })
      .mockResolvedValue({ jobs: [job({ status: 'succeeded', frames_done: 8 })] })
    await renderPanel()
    expect(mockedList).toHaveBeenCalledTimes(1)

    await act(() => vi.advanceTimersByTimeAsync(POLL_MS))
    expect(mockedList).toHaveBeenCalledTimes(2)
    expect(screen.getByText('完了')).toBeTruthy()

    await act(() => vi.advanceTimersByTimeAsync(POLL_MS * 5))
    expect(mockedList).toHaveBeenCalledTimes(2)
  })

  it('中止は確認してから送る', async () => {
    mockedList.mockResolvedValue({ jobs: [job({})] })
    vi.mocked(cancelJob).mockResolvedValue(job({ status: 'cancelled' }))
    const confirm = vi.spyOn(window, 'confirm').mockReturnValueOnce(false).mockReturnValueOnce(true)
    await renderPanel()

    await act(async () => fireEvent.click(screen.getByRole('button', { name: '中止' })))
    expect(cancelJob).not.toHaveBeenCalled()
    await act(async () => fireEvent.click(screen.getByRole('button', { name: '中止' })))
    expect(cancelJob).toHaveBeenCalledWith('j1')
    confirm.mockRestore()
  })
})

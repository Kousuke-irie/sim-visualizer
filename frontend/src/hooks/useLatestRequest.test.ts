// @vitest-environment jsdom
import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useLatestRequest } from './useLatestRequest'

type Req = { id: number }

function deferred<T>() {
  let resolve!: (v: T) => void
  let reject!: (e: Error) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe('useLatestRequest', () => {
  it('request が null の間は取得しない', () => {
    const fetcher = vi.fn()
    const { result } = renderHook(() => useLatestRequest<Req, string>(null, fetcher))
    expect(fetcher).not.toHaveBeenCalled()
    expect(result.current).toEqual({ data: null, loading: false, error: null })
  })

  it('取得中は loading、完了で data', async () => {
    const d = deferred<string>()
    const { result } = renderHook(() => useLatestRequest<Req, string>({ id: 1 }, () => d.promise))
    expect(result.current.loading).toBe(true)
    await act(async () => d.resolve('one'))
    expect(result.current).toEqual({ data: 'one', loading: false, error: null })
  })

  it('同じ内容の request を作り直しても取り直さない（再描画のたびに通信しない）', async () => {
    const fetcher = vi.fn().mockResolvedValue('one')
    const { rerender } = renderHook(({ req }) => useLatestRequest<Req, string>(req, fetcher), {
      initialProps: { req: { id: 1 } },
    })
    rerender({ req: { id: 1 } })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(1))
    rerender({ req: { id: 2 } })
    await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2))
  })

  it('後から出したリクエストより遅れて返った古い応答は捨てる', async () => {
    const slow = deferred<string>()
    const fast = deferred<string>()
    const fetcher = vi.fn((req: Req) => (req.id === 1 ? slow.promise : fast.promise))
    const { result, rerender } = renderHook(({ req }) => useLatestRequest<Req, string>(req, fetcher), {
      initialProps: { req: { id: 1 } },
    })
    rerender({ req: { id: 2 } })
    await act(async () => fast.resolve('new'))
    await act(async () => slow.resolve('stale'))
    expect(result.current.data).toBe('new')
  })

  it('失敗したらエラーを出し、直前のデータは表示し続ける', async () => {
    const fetcher = vi.fn((req: Req) => (req.id === 1 ? Promise.resolve('one') : Promise.reject(new Error('boom'))))
    const { result, rerender } = renderHook(({ req }) => useLatestRequest<Req, string>(req, fetcher), {
      initialProps: { req: { id: 1 } },
    })
    await waitFor(() => expect(result.current.data).toBe('one'))
    rerender({ req: { id: 2 } })
    await waitFor(() => expect(result.current.error).toBe('boom'))
    expect(result.current).toEqual({ data: 'one', loading: false, error: 'boom' })
  })
})

import { afterEach, describe, expect, it, vi } from 'vitest'
import { fetchSectionData, formatErrorDetail } from './client'

describe('formatErrorDetail', () => {
  it('文字列の detail（業務エラー）はそのまま表示する', () => {
    expect(formatErrorDetail('input.dat が見つかりません', 'fallback')).toBe('input.dat が見つかりません')
  })

  it('422 の検証エラー配列は「項目: メッセージ」に整形する（[object Object] にしない）', () => {
    const detail = [
      { loc: ['body', 'plane'], msg: "Input should be 'XY', 'XZ' or 'YZ'", type: 'literal_error' },
      { loc: ['body', 'slice_index'], msg: 'Field required', type: 'missing' },
    ]
    expect(formatErrorDetail(detail, 'fallback')).toBe(
      "入力が不正です: plane: Input should be 'XY', 'XZ' or 'YZ' / slice_index: Field required",
    )
  })

  it('想定外の形や空なら fallback', () => {
    expect(formatErrorDetail(undefined, 'fallback')).toBe('fallback')
    expect(formatErrorDetail({ foo: 1 }, 'fallback')).toBe('fallback')
    expect(formatErrorDetail([], 'fallback')).toBe('fallback')
  })
})

describe('API エラーの伝搬', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('422 応答を整形済みメッセージの Error として投げる', async () => {
    const body = { detail: [{ loc: ['body', 'plane'], msg: 'bad plane', type: 'x' }] }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 422 })))

    await expect(
      fetchSectionData({ file_id: 'f', plane: 'XY', slice_index: 0, variable: 'TEMP', include_vectors: true }),
    ).rejects.toThrow('入力が不正です: plane: bad plane')
  })

  it('JSON でない応答（プロキシのエラーページ等）はステータス付きの既定メッセージ', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('<html>Bad Gateway</html>', { status: 502 })))

    await expect(
      fetchSectionData({ file_id: 'f', plane: 'XY', slice_index: 0, variable: 'TEMP', include_vectors: true }),
    ).rejects.toThrow('データ取得に失敗しました (502)')
  })
})

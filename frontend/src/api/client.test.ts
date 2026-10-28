import { afterEach, describe, expect, it, vi } from 'vitest'
import * as client from './client'
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

describe('各 API 関数のリクエスト', () => {
  afterEach(() => vi.unstubAllGlobals())

  function stubOk(body: unknown = {}) {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 }))
    vi.stubGlobal('fetch', fetchMock)
    return fetchMock
  }

  const file = new File(['x'], 'tec-00000.plt')
  const sectionReq = { file_id: 'f', plane: 'XY' as const, slice_index: 1, variable: 'TEMP', include_vectors: true }
  const dirSectionReq = {
    dir_id: 'd',
    frame_index: 2,
    plane: 'YZ' as const,
    slice_index: 0,
    variable: 'DOX',
    include_vectors: true,
  }
  const tsReq = { dir_id: 'd', param: 'DOX', point: '01' }

  it.each([
    ['uploadPlt', () => client.uploadPlt(file), '/api/upload', 'POST', 'form'],
    ['uploadDat', () => client.uploadDat(file), '/api/upload', 'POST', 'form'],
    ['fetchSectionData', () => client.fetchSectionData(sectionReq), '/api/section/data', 'POST', sectionReq],
    ['fetchTimeseriesData', () => client.fetchTimeseriesData('a b'), '/api/timeseries/data/a%20b', 'GET', null],
    ['browseDirectory()', () => client.browseDirectory(), '/api/directory/browse', 'GET', null],
    [
      'browseDirectory(path)',
      () => client.browseDirectory('/data/湾 A'),
      `/api/directory/browse?path=${encodeURIComponent('/data/湾 A')}`,
      'GET',
      null,
    ],
    ['openDirectory', () => client.openDirectory('/data/sim'), '/api/directory/open', 'POST', { path: '/data/sim' }],
    ['fetchDirectoryMeta', () => client.fetchDirectoryMeta('d'), '/api/directory/d/meta', 'GET', null],
    [
      'fetchDirectorySectionData',
      () => client.fetchDirectorySectionData(dirSectionReq),
      '/api/directory/section/data',
      'POST',
      dirSectionReq,
    ],
    [
      'fetchDirectoryTimeseriesData',
      () => client.fetchDirectoryTimeseriesData(tsReq),
      '/api/directory/timeseries/data',
      'POST',
      tsReq,
    ],
  ] as const)('%s', async (name, call, url, method, body) => {
    // アップロードは返ってきた kind を確かめるので、それぞれの種類を返す
    const kind = name === 'uploadDat' ? 'dat' : 'plt'
    const fetchMock = stubOk({ ok: true, kind })
    await expect(call()).resolves.toMatchObject({ ok: true })

    const [calledUrl, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined]
    expect(calledUrl).toBe(url)
    expect(init?.method ?? 'GET').toBe(method)
    if (body === 'form') {
      expect(init?.body).toBeInstanceOf(FormData)
      expect((init?.body as FormData).get('file')).toBeInstanceOf(File)
    } else if (body) {
      expect(JSON.parse(init?.body as string)).toEqual(body)
      expect(new Headers(init?.headers).get('Content-Type')).toBe('application/json')
    } else {
      expect(init?.body).toBeUndefined()
    }
  })
})

describe('アップロードの種類チェック', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('.plt を期待した呼び出しに .dat のメタ情報が返ったらエラーにする', async () => {
    const body = { kind: 'dat', file_id: 'f' }
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status: 200 })))
    await expect(client.uploadPlt(new File(['x'], 'a.dat'))).rejects.toThrow('想定と異なる種類のファイルです')
  })
})

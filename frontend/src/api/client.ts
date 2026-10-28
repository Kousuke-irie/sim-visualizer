import type {
  DatMeta,
  DirectoryBrowseResponse,
  DirectoryMeta,
  DirectorySectionDataRequest,
  DirectorySectionDataResponse,
  DirectoryTimeseriesRequest,
  DirectoryTimeseriesResponse,
  PltMeta,
  SectionDataRequest,
  SectionDataResponse,
  TimeseriesDataResponse,
} from '../types'

const BASE = '/api'

type ValidationIssue = { loc?: unknown[]; msg?: unknown }

// バックエンドの業務エラーは detail が日本語の文字列だが、FastAPI の 422（リクエスト検証エラー）は
// detail がオブジェクトの配列になる。そのまま Error に渡すと "[object Object]" と表示されるため整形する。
export function formatErrorDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail) return detail
  if (Array.isArray(detail) && detail.length > 0) {
    const parts = (detail as ValidationIssue[]).map((issue) => {
      // loc の先頭は 'body' / 'query' などの位置なので、項目名だけを残す
      const field = Array.isArray(issue.loc) ? issue.loc.slice(1).join('.') : ''
      const msg = typeof issue.msg === 'string' ? issue.msg : ''
      return field ? `${field}: ${msg}` : msg
    })
    return `入力が不正です: ${parts.join(' / ')}`
  }
  return fallback
}

async function safeErrorMessage(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json()
    return formatErrorDetail(body?.detail, fallback)
  } catch {
    return fallback
  }
}

export async function uploadPlt(file: File): Promise<PltMeta> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `アップロードに失敗しました (${res.status})`))
  }
  return res.json()
}

export async function fetchSectionData(req: SectionDataRequest): Promise<SectionDataResponse> {
  const res = await fetch(`${BASE}/section/data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `データ取得に失敗しました (${res.status})`))
  }
  return res.json()
}

export async function uploadDat(file: File): Promise<DatMeta> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/upload`, { method: 'POST', body: form })
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `アップロードに失敗しました (${res.status})`))
  }
  return res.json()
}

export async function fetchTimeseriesData(fileId: string): Promise<TimeseriesDataResponse> {
  const res = await fetch(`${BASE}/timeseries/data/${fileId}`)
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `データ取得に失敗しました (${res.status})`))
  }
  return res.json()
}

export async function browseDirectory(path?: string): Promise<DirectoryBrowseResponse> {
  const url = path ? `${BASE}/directory/browse?path=${encodeURIComponent(path)}` : `${BASE}/directory/browse`
  const res = await fetch(url)
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `ディレクトリ一覧の取得に失敗しました (${res.status})`))
  }
  return res.json()
}

export async function openDirectory(path: string): Promise<DirectoryMeta> {
  const res = await fetch(`${BASE}/directory/open`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ path }),
  })
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `ディレクトリを開けませんでした (${res.status})`))
  }
  return res.json()
}

export async function fetchDirectoryMeta(dirId: string): Promise<DirectoryMeta> {
  const res = await fetch(`${BASE}/directory/${dirId}/meta`)
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `データ取得に失敗しました (${res.status})`))
  }
  return res.json()
}

export async function fetchDirectorySectionData(
  req: DirectorySectionDataRequest,
): Promise<DirectorySectionDataResponse> {
  const res = await fetch(`${BASE}/directory/section/data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `データ取得に失敗しました (${res.status})`))
  }
  return res.json()
}

export async function fetchDirectoryTimeseriesData(
  req: DirectoryTimeseriesRequest,
): Promise<DirectoryTimeseriesResponse> {
  const res = await fetch(`${BASE}/directory/timeseries/data`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `データ取得に失敗しました (${res.status})`))
  }
  return res.json()
}

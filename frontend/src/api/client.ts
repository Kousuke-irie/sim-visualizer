import type {
  CompareCheckRequest,
  CompareCheckResponse,
  CompareSectionRequest,
  CompareSectionResponse,
  CompareTimeseriesRequest,
  CompareTimeseriesResponse,
  CreateRunRequest,
  CreatedRun,
  RunPreview,
  RunTemplate,
  RunTemplateRequest,
  DatMeta,
  DirectoryBrowseResponse,
  DirectoryMeta,
  DirectoryOpenRequest,
  DirectorySectionDataRequest,
  DirectorySectionDataResponse,
  DirectoryTimeseriesRequest,
  DirectoryTimeseriesResponse,
  PltMeta,
  SectionDataRequest,
  SectionDataResponse,
  TimeseriesDataResponse,
  UploadedMeta,
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

const FETCH_FAILED = 'データ取得に失敗しました'

// 全 API 呼び出しの共通処理。失敗時はサーバーの detail（なければ「既定文 (ステータス)」）を Error にする
async function request<T>(path: string, init: RequestInit | undefined, failure: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, init)
  if (!res.ok) {
    throw new Error(await safeErrorMessage(res, `${failure} (${res.status})`))
  }
  return res.json()
}

function postJson<T>(path: string, body: unknown, failure = FETCH_FAILED): Promise<T> {
  return request<T>(
    path,
    { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) },
    failure,
  )
}

function getJson<T>(path: string, failure = FETCH_FAILED): Promise<T> {
  return request<T>(path, undefined, failure)
}

// /api/upload は拡張子で .plt / .dat を判定し、kind で区別できるメタ情報を返す
async function uploadFile(file: File): Promise<UploadedMeta> {
  const form = new FormData()
  form.append('file', file)
  return request<UploadedMeta>('/upload', { method: 'POST', body: form }, 'アップロードに失敗しました')
}

function expectKind<K extends UploadedMeta['kind']>(meta: UploadedMeta, kind: K): Extract<UploadedMeta, { kind: K }> {
  if (meta.kind !== kind) {
    throw new Error(`想定と異なる種類のファイルです（期待: .${kind}、実際: .${meta.kind}）`)
  }
  return meta as Extract<UploadedMeta, { kind: K }>
}

export async function uploadPlt(file: File): Promise<PltMeta> {
  return expectKind(await uploadFile(file), 'plt')
}

export async function uploadDat(file: File): Promise<DatMeta> {
  return expectKind(await uploadFile(file), 'dat')
}

export function fetchSectionData(req: SectionDataRequest): Promise<SectionDataResponse> {
  return postJson('/section/data', req)
}

export function fetchTimeseriesData(fileId: string): Promise<TimeseriesDataResponse> {
  return getJson(`/timeseries/data/${encodeURIComponent(fileId)}`)
}

export function browseDirectory(path?: string): Promise<DirectoryBrowseResponse> {
  const query = path ? `?path=${encodeURIComponent(path)}` : ''
  return getJson(`/directory/browse${query}`, 'ディレクトリ一覧の取得に失敗しました')
}

export function openDirectory(path: string): Promise<DirectoryMeta> {
  return postJson('/directory/open', { path } satisfies DirectoryOpenRequest, 'ディレクトリを開けませんでした')
}

export function fetchDirectoryMeta(dirId: string): Promise<DirectoryMeta> {
  return getJson(`/directory/${encodeURIComponent(dirId)}/meta`)
}

export function fetchDirectorySectionData(req: DirectorySectionDataRequest): Promise<DirectorySectionDataResponse> {
  return postJson('/directory/section/data', req)
}

export function fetchDirectoryTimeseriesData(req: DirectoryTimeseriesRequest): Promise<DirectoryTimeseriesResponse> {
  return postJson('/directory/timeseries/data', req)
}

export function compareCheck(req: CompareCheckRequest): Promise<CompareCheckResponse> {
  return postJson('/compare/check', req, '比較できるか確認できませんでした')
}

export function fetchCompareSection(req: CompareSectionRequest): Promise<CompareSectionResponse> {
  return postJson('/compare/section', req)
}

export function fetchCompareTimeseries(req: CompareTimeseriesRequest): Promise<CompareTimeseriesResponse> {
  return postJson('/compare/timeseries', req)
}

// 新しいランの作成はホストの runner が行う。runner が起動していなければ 503 と起動方法が返る
export function fetchRunTemplate(req: RunTemplateRequest): Promise<RunTemplate> {
  return postJson('/runs/template', req, '新しいランの準備ができませんでした')
}

export function previewRun(req: CreateRunRequest): Promise<RunPreview> {
  return postJson('/runs/preview', req, '確認できませんでした')
}

export function createRun(req: CreateRunRequest): Promise<CreatedRun> {
  return postJson('/runs', req, '新しいランを作れませんでした')
}

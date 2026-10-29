import { execFileSync } from 'node:child_process'
import { mkdtempSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import type { Page, Request } from '@playwright/test'
import { E2E_DATA_ROOT } from './dataRoot'

const BACKEND_DIR = resolve(dirname(fileURLToPath(import.meta.url)), '../../backend')

// backend/app/tests/sample_data.py で、実データと同じ形式の合成計算結果ディレクトリを作る。
// 格子 I=4, J=5, K=3、フレーム 3 枚（ifit2=3600s）、hist は TEMP/DOX × 地点 01/02。
export function createSimulationDir(options: { tempOffset?: number; ni?: number; name?: string } = {}): string {
  const root = join(mkdtempSync(join(E2E_DATA_ROOT, 'case-')), options.name ?? 'sim')
  const args = ['-m', 'app.tests.sample_data', root]
  if (options.tempOffset !== undefined) args.push('--temp-offset', String(options.tempOffset))
  if (options.ni !== undefined) args.push('--ni', String(options.ni))
  execFileSync(process.env.PYTHON ?? 'python', args, { cwd: BACKEND_DIR })
  return root
}

// /api への通信を記録する。「見た目の変更では通信しない」ことの検証に使う。
export function recordApiRequests(page: Page): Request[] {
  const requests: Request[] = []
  page.on('request', (req) => {
    if (new URL(req.url()).pathname.startsWith('/api/')) requests.push(req)
  })
  return requests
}

// 表示中の Plotly 図のトレース（div.js-plotly-plot に付与される data プロパティ）を読む。
// 非表示のタブも状態保持のためマウントしたままなので、見えている図に限定する
export async function plotTraces(page: Page): Promise<Record<string, unknown>[]> {
  return page
    .locator('.js-plotly-plot:visible')
    .evaluate((el) => (el as unknown as { data: Record<string, unknown>[] }).data)
}

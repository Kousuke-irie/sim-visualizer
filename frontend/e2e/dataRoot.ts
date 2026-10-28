import { mkdirSync, realpathSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'

// E2E で起動するバックエンドに許可するデータルート。テスト用の計算結果ディレクトリはすべてこの配下に作る
export const E2E_DATA_ROOT = (() => {
  const dir = join(realpathSync(tmpdir()), 'simviz-e2e')
  mkdirSync(dir, { recursive: true })
  return dir
})()

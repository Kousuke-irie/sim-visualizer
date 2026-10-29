import { defineConfig, devices } from '@playwright/test'
import { E2E_DATA_ROOT } from './e2e/dataRoot'

// バックエンド（uvicorn）とフロントエンド（Vite）を実際に起動して、ブラウザから操作する。
// PYTHON でバックエンド用のインタプリタを指定できる（ローカルでは backend/.venv/bin/python など）。
const python = process.env.PYTHON ?? 'python'
// 新しいランの作成はホストの runner が行う。E2E では本物の runner を専用のポートとトークンで起動する
// （手元で 8100 番の runner を動かしていてもぶつからないように）
const RUNNER_PORT = '8101'
const RUNNER_TOKEN = 'e2e-runner-token'

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['github'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: '../backend',
      url: 'http://127.0.0.1:8000/api/health',
      env: {
        SIMVIZ_DATA_ROOTS: E2E_DATA_ROOT,
        SIMVIZ_RUNNER_URL: `http://127.0.0.1:${RUNNER_PORT}`,
        SIMVIZ_RUNNER_TOKEN: RUNNER_TOKEN,
      },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: `${python} -m app.runner`,
      cwd: '../backend',
      // トークン無しの要求には 401 を返すが、Playwright は 401 も「起動済み」とみなす
      url: `http://127.0.0.1:${RUNNER_PORT}/health`,
      env: { SIMVIZ_RUNNER_TOKEN: RUNNER_TOKEN, SIMVIZ_DATA_ROOTS: E2E_DATA_ROOT, SIMVIZ_RUNNER_PORT: RUNNER_PORT },
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      env: { API_PROXY_TARGET: 'http://127.0.0.1:8000' },
      reuseExistingServer: !process.env.CI,
    },
  ],
})

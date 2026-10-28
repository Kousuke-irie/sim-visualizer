import { defineConfig, devices } from '@playwright/test'
import { E2E_DATA_ROOT } from './e2e/dataRoot'

// バックエンド（uvicorn）とフロントエンド（Vite）を実際に起動して、ブラウザから操作する。
// PYTHON でバックエンド用のインタプリタを指定できる（ローカルでは backend/.venv/bin/python など）。
const python = process.env.PYTHON ?? 'python'

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
      env: { SIMVIZ_DATA_ROOTS: E2E_DATA_ROOT },
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

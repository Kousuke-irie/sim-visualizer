import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// docker compose ではサービス名 backend で解決する。E2E/CI のようにホストで直接起動する場合は
// API_PROXY_TARGET で上書きする。
const apiTarget = process.env.API_PROXY_TARGET ?? 'http://backend:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})

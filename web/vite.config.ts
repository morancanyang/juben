import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const target = loadEnv(mode, '.', '').VITE_API_TARGET || 'http://127.0.0.1:8000'
  return {
  plugins: [react()],
  server: { proxy: { '/api': target, '/health': target } },
  build: { sourcemap: false },
}})

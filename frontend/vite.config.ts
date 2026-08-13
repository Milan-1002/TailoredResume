import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // This network has a broken IPv6 loopback path (same issue documented in
    // resume_agent/llm.py) — Vite's default "localhost" bind can silently hang
    // instead of accepting connections. Force IPv4 so `npm run dev` just works.
    host: '127.0.0.1',
  },
})

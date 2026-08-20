// vite.config.js
// ─────────────────────────────────────────────────────────────────
// WHY proxy?
//   In dev, your React app is on :5173 and backend on :8000.
//   Instead of writing full URLs (http://localhost:8000/api/...) in
//   every fetch call, you proxy /api requests through Vite.
//   This also avoids CORS issues during local development.
// ─────────────────────────────────────────────────────────────────

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',    // Required for Docker — listen on all interfaces
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000',  // Docker service name
        changeOrigin: true,
      }
    }
  }
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
    allowedHosts: true,
    proxy: {
      '/api/v1': {
        target: 'https://storelex.store/toing_web/api',
        rewrite: (path) => path.replace(/^\/api\/v1/, ''),
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: 'https://storelex.store/toing_web/api',
        rewrite: (path) => path.replace(/^\/api/, ''),
        changeOrigin: true,
        secure: false,
      }
    }
  },
  preview: {
    port: 5173,
    host: true,
    proxy: {
      '/api/v1': {
        target: 'https://storelex.store/toing_web/api',
        rewrite: (path) => path.replace(/^\/api\/v1/, ''),
        changeOrigin: true,
        secure: false,
      },
      '/api': {
        target: 'https://storelex.store/toing_web/api',
        rewrite: (path) => path.replace(/^\/api/, ''),
        changeOrigin: true,
        secure: false,
      }
    }
  }
})

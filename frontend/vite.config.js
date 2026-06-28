import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host:  '0.0.0.0',
    port:  5173,
    watch: {
      usePolling: true,    // needed inside Docker on Windows
    },
    proxy: {
      '/api': {
        target:       'http://api:8000',   // Docker service name
        changeOrigin: true,
      },
    },
  },
})
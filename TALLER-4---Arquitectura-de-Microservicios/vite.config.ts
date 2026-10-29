import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    host: '0.0.0.0',
    port: Number.parseInt(process.env.PORT || '5173'),
    strictPort: true,
    proxy: {
      '/api/productos': 'http://127.0.0.1:8001',
      '/api/clientes': 'http://127.0.0.1:8002',
      '/api/pedidos': 'http://127.0.0.1:8003',
    },
  },
  preview: {
    host: '0.0.0.0',
    port: Number.parseInt(process.env.PORT || '4173'),
  },
})

import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5200,
    strictPort: true,  // fail loudly if 5200 is taken instead of silently bumping
  },
})

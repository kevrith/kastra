import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5200,
    strictPort: true,  // fail loudly if 5200 is taken instead of silently bumping
  },
  test: {
    // Component tests need a DOM; the pure util tests run fine in it too.
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
    // Vite would otherwise try to serve these as app routes.
    include: ['src/**/*.{test,spec}.{js,jsx}'],
  },
})

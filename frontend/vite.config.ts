import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // Relative base so built asset URLs resolve under Electron's file://
  // protocol (Phase 5) - an absolute "/" base would 404 there.
  base: './',
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
  },
})

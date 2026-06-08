import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'fs'

// Only use local HTTPS certs in dev — they won't exist in CI/Docker builds
const httpsConfig = (() => {
  try {
    return {
      key: fs.readFileSync('./localhost+1-key.pem'),
      cert: fs.readFileSync('./localhost+1.pem'),
    };
  } catch {
    return undefined;
  }
})();

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
  server: {
    port: 5173,
    strictPort: true,
    https: httpsConfig,
    proxy: {
      '/auth/login': 'http://localhost:8000',
      '/auth/token': 'http://localhost:8000',
      '/api': 'http://localhost:8000',
    },
  },
})

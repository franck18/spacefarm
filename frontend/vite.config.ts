import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// During development, route API requests through Vite so the browser stays same-origin.
export default defineConfig({ plugins: [react()], server: { port: 5180, strictPort: true,
  proxy: { '/api': { target: 'http://169.254.82.190:8000', changeOrigin: true } },
} });

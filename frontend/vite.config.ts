import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    // browserRestore.test.ts uses Node APIs only — keep the default node environment.
    // App.test.tsx opts in to jsdom via the @vitest-environment jsdom docblock comment.
    environment: 'node',
    setupFiles: ['./src/tests/setup.ts'],
    globals: true,
  },
});


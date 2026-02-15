import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: 'localhost',
    port: 5173,
    strictPort: false,
  },
  build: {
    sourcemap: false,
    target: 'es2020',
  },
});

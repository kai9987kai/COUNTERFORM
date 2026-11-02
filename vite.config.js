import { defineConfig } from 'vite';
export default defineConfig({
  root: 'web',
  base: './',
  build: { outDir: '../counterform/web', emptyOutDir: true, sourcemap: false },
  server: { proxy: { '/api': 'http://127.0.0.1:8768' } },
});

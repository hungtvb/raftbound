import { defineConfig } from 'vite';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const root = dirname(fileURLToPath(import.meta.url));

export default defineConfig({
  root,
  publicDir: resolve(root, '../game/assets'),
  base: './',
  build: { outDir: resolve(root, 'dist'), emptyOutDir: true, target: 'es2022' },
  server: { fs: { allow: [resolve(root, '..')] } },
});

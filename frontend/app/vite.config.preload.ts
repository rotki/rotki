import { builtinModules } from 'node:module';
import { join } from 'node:path';
import process from 'node:process';
import { defineConfig } from 'vite';

const PACKAGE_ROOT = __dirname;
const isDevelopment = process.env.NODE_ENV === 'development';

export default defineConfig({
  root: PACKAGE_ROOT,
  envDir: process.cwd(),
  resolve: {
    alias: {
      '@electron': `${join(PACKAGE_ROOT, 'electron')}/`,
      '@shared': `${join(PACKAGE_ROOT, 'shared')}/`,
    },
  },
  build: {
    sourcemap: isDevelopment ? 'inline' : false,
    outDir: 'dist',
    assetsDir: '.',
    target: 'node22',
    ssr: true,
    minify: !isDevelopment,
    lib: {
      entry: 'electron/preload/index.ts',
      formats: ['cjs'],
    },
    rollupOptions: {
      external: ['electron', ...builtinModules.flatMap(p => [p, `node:${p}`])],
      output: {
        entryFileNames: 'preload.js',
      },
    },
    emptyOutDir: false,
  },
  esbuild: {
    target: 'node22',
  },
});

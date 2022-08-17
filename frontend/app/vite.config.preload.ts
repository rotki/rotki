import { builtinModules } from 'module';
import { join } from 'path';
import { defineConfig } from 'vite';

const PACKAGE_ROOT = __dirname;
const isDevelopment = process.env.NODE_ENV === 'development';

export default defineConfig({
  root: PACKAGE_ROOT,
  envDir: process.cwd(),
  resolve: {
    alias: {
      '@': join(PACKAGE_ROOT, 'src') + '/'
    }
  },
  build: {
    sourcemap: isDevelopment ? 'inline' : false,
    outDir: 'dist',
    assetsDir: '.',
    minify: !isDevelopment,
    lib: {
      entry: 'src/preload.ts',
      formats: ['cjs']
    },
    rollupOptions: {
      external: ['electron', ...builtinModules.flatMap(p => [p, `node:${p}`])],
      output: {
        entryFileNames: '[name].js'
      }
    },
    emptyOutDir: false
  }
});

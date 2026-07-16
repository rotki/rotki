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
  ssr: {
    noExternal: true,
  },
  build: {
    sourcemap: isDevelopment ? 'inline' : false,
    target: 'node24',
    outDir: 'dist',
    assetsDir: '.',
    ssr: true,
    minify: !isDevelopment,
    lib: {
      entry: 'electron/main/index.ts',
      formats: ['es'],
    },
    rolldownOptions: {
      // httpxy is only loaded via dynamic import on the dev proxy path
      // (see AppServer.startDevelopmentProxy); keep it out of the production bundle.
      external: ['electron', 'httpxy', ...builtinModules.flatMap(p => [p, `node:${p}`])],
      output: {
        entryFileNames: 'main.js',
        manualChunks(id) {
          if (id.includes('node_modules'))
            return 'background-vendor';
          if (id.includes('electron-updater'))
            return 'background-vendor-updater';
          if (id.includes('http'))
            return 'background-http';
        },
      },
    },
    emptyOutDir: false,
  },
  oxc: {
    target: 'node24',
  },
});

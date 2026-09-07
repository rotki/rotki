import { builtinModules } from 'node:module';
import { join } from 'node:path';
import process from 'node:process';
import { defineConfig } from 'vite';

const PACKAGE_ROOT = import.meta.dirname;
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
      // httpxy is dynamically imported on the dev proxy path only, so it stays out of production.
      external: ['electron', 'httpxy', ...builtinModules.flatMap(p => [p, `node:${p}`])],
      output: {
        entryFileNames: 'main.js',
        /**
         * Keeps our code in `main.js` and dependencies in `background-vendor`, so a stack frame
         * from the minified production bundle, which ships no sourcemaps, says which side it came
         * from.
         *
         * Only statically reachable dependencies are claimed. A blanket `node_modules` test also
         * swallows lazily imported subtrees, and since `background-vendor` is itself statically
         * imported by the entry, that silently drags them back into the startup path: it is what
         * kept electron-updater's 290 KB eager. Reachability is derived from the module graph
         * rather than a hand-listed exclusion, so it stays correct as dependencies move around. A
         * module needed by both sides is statically reachable, lands in the vendor chunk, and the
         * lazy chunk imports it from there.
         */
        manualChunks(id, { getModuleInfo }) {
          if (!id.includes('node_modules'))
            return;

          const seen = new Set<string>();
          const reachedStatically = (moduleId: string): boolean => {
            if (seen.has(moduleId))
              return false;
            seen.add(moduleId);
            const info = getModuleInfo(moduleId);
            if (!info)
              return false;
            return info.isEntry || info.importers.some(reachedStatically);
          };

          return reachedStatically(id) ? 'background-vendor' : undefined;
        },
      },
    },
    emptyOutDir: false,
  },
  oxc: {
    target: 'node24',
  },
});

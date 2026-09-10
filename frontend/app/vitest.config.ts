import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { configDefaults, defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config.ts';

/*
 * `test.env` is applied inside the worker, which is too late for a `vmThreads` V8 context: the
 * context builds its `Date` from the timezone the process started with, so a spec pinning the
 * clock reads host-local hours and drifts by the local offset. Setting it here, on the parent,
 * means every worker inherits it before its context exists. `test.env` keeps it for the runtime.
 */
process.env.TZ = 'UTC';

export default mergeConfig(
  mergeConfig(viteConfig, {
    resolve: {
      alias: {
        '@test': `${path.join(import.meta.dirname, 'tests', 'unit')}/`,
        '@electron': `${path.join(import.meta.dirname, 'electron')}/`,
      },
    },
  }),
  defineConfig({
    test: {
      globals: true,
      environment: 'happy-dom',
      /*
       * `vmThreads` builds the happy-dom environment once per worker instead of once per file,
       * which was a quarter of the run across 1111 files. `vmMemoryLimit` is not optional here:
       * this pool does not reclaim contexts reliably, and without a limit the run holds ~17GB
       * against ~5GB for the default pool, which does not fit a CI runner. It is a top-level
       * option, not a `poolOptions` one, so a misplaced key silently does nothing.
       */
      pool: 'vmThreads',
      vmMemoryLimit: '512MB',
      testTimeout: 15_000,
      env: {
        TZ: 'UTC',
        VITE_TEST: 'true',
      },
      fakeTimers: {
        toFake: [
          'setTimeout',
          'clearTimeout',
          'setInterval',
          'clearInterval',
          'setImmediate',
          'clearImmediate',
          'Date',
        ],
      },
      exclude: [...configDefaults.exclude, 'tests/e2e/**'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      server: {
        deps: {
          inline: ['@rotki/ui-library'],
        },
      },
      setupFiles: ['tests/unit/setup-files/vm-globals.ts', 'tests/unit/setup-files/setup.ts'],
      coverage: {
        provider: 'v8',
        reportsDirectory: 'tests/unit/coverage',
        reporter: ['json', 'lcov', 'html'],
        include: ['src/**'],
        exclude: [
          'node_modules',
          'tests/',
          '**/*.d.ts',
          '**/*.spec.ts',
          'src/App.vue',
          'src/DevApp.vue',
          'src/i18n.ts',
          'src/main.ts',
          'src/modules/shell/app/store-debug-plugin.ts',
          'src/pages/playground/**',
        ],
      },
    },
  }),
);

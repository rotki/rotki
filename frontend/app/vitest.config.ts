import { availableParallelism } from 'node:os';
import path from 'node:path';
import process from 'node:process';
import { fileURLToPath } from 'node:url';
import { configDefaults, defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config.ts';

/*
 * Set on the parent because `test.env` applies inside the worker, too late for a `vmThreads` V8
 * context: it builds `Date` from the process's starting timezone, so a pinned clock drifts by the
 * local offset. `test.env` keeps it for the runtime.
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
       * A click on a `target="_blank"` link opens a child page, which happy-dom then loads for real:
       * a spec clicking a docs link sent requests to docs.rotki.com from every run.
       */
      environmentOptions: {
        happyDOM: {
          settings: {
            navigation: {
              disableChildPageNavigation: true,
            },
          },
        },
      },
      /*
       * `vmThreads` builds happy-dom once per worker; per file, that setup was a quarter of the run.
       * `vmMemoryLimit` is required: this pool does not reclaim contexts reliably, and without it the
       * run outgrows a CI runner. It is top-level, not `poolOptions`; a misplaced key does nothing.
       */
      pool: 'vmThreads',
      vmMemoryLimit: '512MB',
      /*
       * Each worker holds its own happy-dom context and module graph, so memory grows with the
       * worker count while the run stops getting faster at about six. Capped below the core count
       * as well, so a small runner keeps the default of one worker per spare core.
       */
      maxWorkers: Math.min(6, availableParallelism() - 1),
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
        reporter: ['lcov', 'html'],
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

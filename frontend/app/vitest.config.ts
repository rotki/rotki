import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { merge } from 'es-toolkit';
import { configDefaults, defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  merge(viteConfig, {
    resolve: {
      alias: {
        '@test': `${path.join(__dirname, 'tests', 'unit')}/`,
      },
    },
  }),
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
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
      setupFiles: ['tests/unit/setup-files/setup.ts'],
      coverage: {
        provider: 'v8',
        reportsDirectory: 'tests/unit/coverage',
        reporter: ['json'],
        include: ['src/*'],
        exclude: ['node_modules', 'tests/', '**/*.d.ts', '**/*.spec.ts'],
      },
    },
  }),
);

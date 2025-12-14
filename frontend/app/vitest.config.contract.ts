import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { merge } from 'es-toolkit';
import { defineConfig, mergeConfig } from 'vitest/config';
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
      environment: 'node',
      testTimeout: 30_000,
      env: {
        TZ: 'UTC',
        VITE_TEST: 'true',
      },
      include: ['tests/contract/**/*.spec.ts'],
      root: fileURLToPath(new URL('./', import.meta.url)),
      server: {
        deps: {
          inline: ['@rotki/ui-library'],
        },
      },
      coverage: {
        provider: 'v8',
        reportsDirectory: 'tests/contract/coverage',
        reporter: ['json', 'lcov', 'html'],
        include: ['src/*'],
        exclude: ['node_modules', 'tests/', '**/*.d.ts', '**/*.spec.ts'],
      },
    },
  }),
);

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { merge } from 'es-toolkit';
import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

/**
 * Contract test mode (measurement framework §5.1).
 *
 * Runs the API-composable contract tests against a LIVE backend booted on a
 * golden user profile, exercising the full real client pipeline (URL
 * construction, snake_case<->camelCase transforms and zod parsing) instead of
 * MSW fixtures. Run through `pnpm run test:contract`, which boots the backend
 * and provides CONTRACT_BACKEND_URL.
 *
 * Deliberately separate from vitest.config.ts: no MSW setup file, no fake
 * timers (real HTTP needs real timers) and no parallelism (the backend is a
 * single-user process).
 */
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
      environment: 'happy-dom',
      testTimeout: 30_000,
      env: {
        TZ: 'UTC',
        VITE_TEST: 'true',
      },
      include: ['tests/contract/**/*.contract.ts'],
      fileParallelism: false,
      root: fileURLToPath(new URL('./', import.meta.url)),
      setupFiles: ['tests/contract/setup.ts'],
    },
  }),
);

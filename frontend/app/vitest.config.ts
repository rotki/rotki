import { fileURLToPath } from 'node:url';
import { configDefaults, defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

export default mergeConfig(
  viteConfig,
  defineConfig({
    test: {
      globals: true,
      environment: 'jsdom',
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
        exclude: ['node_modules', 'tests/', '**/*.d.ts'],
      },
    },
  }),
);

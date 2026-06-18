import path from 'node:path';

import rotki from '@rotki/eslint-config';
import { translationKeys } from '@rotki/ui-library';

// Pre-load the ESM-only ESLint parsers before the config factories run.
// @intlify/eslint-plugin-vue-i18n require()s them while eslint composes configs
// via Promise.all; warming them here avoids Node's ERR_REQUIRE_ESM_RACE_CONDITION.
import 'jsonc-eslint-parser';
import 'yaml-eslint-parser';

export default rotki({
  ignores: ['app/backend-icons.generated.ts', 'app/tests/e2e/test-results/**'],
  vue: true,
  typescript: {
    tsconfigPath: 'tsconfig.json',
  },
  stylistic: true,
  rotki: {
    src: path.join('app', 'src'),
    ignoreKeys: [
      '/backend_mappings.*/',
      '/notification_messages.missing_api_key.*/',
      '/premium_components.*/',
      '/transactions.query_status.*/',
      '/transactions.query_status_events.*/',
      '/transactions.events.headers.*/',
      ...translationKeys(),
    ],
    overrides: {
      '@rotki/consistent-ref-type-annotation': ['error', {
        allowInference: true,
      }],
      '@rotki/no-dot-ts-imports': 'error',
    },
  },
  imports: {
    overrides: {
      '@rotki/max-dependencies': ['error', { max: 20 }],
    },
  },
  vueI18n: {
    src: path.join('app', 'src'),
    overrides: {
      '@intlify/vue-i18n/no-i18n-t-path-prop': 'error',
      '@intlify/vue-i18n/no-deprecated-i18n-component': 'error',
    },
  },
}, {
  files: ['**/*.ts', '**/*.vue'],
  rules: {
    '@typescript-eslint/consistent-type-assertions': ['warn', {
      assertionStyle: 'never',
    }],
  },
}, {
  files: ['**/src/**/*.ts'],
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
  },
}, {
  files: ['**/locales/**/*.json'],
  rules: {
    'jsonc/sort-keys': ['error', 'asc', {
      caseSensitive: true,
      natural: true,
    }],
  },
});

import path from 'node:path';
import rotki from '@rotki/eslint-config';
import { translationKeys } from '@rotki/ui-library';

export default rotki({
  vue: true,
  typescript: {
    tsconfigPath: 'tsconfig.json',
  },
  stylistic: true,
  rotki: {
    overrides: {
      '@rotki/consistent-ref-type-annotation': ['error', {
        allowInference: true,
      }],
      '@rotki/no-dot-ts-imports': 'error',
    },
  },
  imports: {
    overrides: {
      '@rotki/max-dependencies': ['warn', { max: 20 }],
    },
  },
  vueI18n: {
    src: path.join('app', 'src'),
    ignores: [
      '/backend_mappings.*/',
      '/notification_messages.missing_api_key.*/',
      '/premium_components.*/',
      '/transactions.query_status.*/',
      '/transactions.query_status_events.*/',
      '/transactions.events.headers.*/',
      ...translationKeys(),
    ],
    overrides: {
      '@intlify/vue-i18n/no-i18n-t-path-prop': 'error',
      '@intlify/vue-i18n/no-deprecated-i18n-component': 'error',
    },
    enableNoUnusedKeys: 'ci',
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

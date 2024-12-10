import path from 'node:path';
import rotki from '@rotki/eslint-config';

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
  cypress: {
    testDirectory: path.join('app', 'tests', 'e2e'),
  },
  imports: {
    overrides: {
      'import/no-cycle': 'off',
      'import/max-dependencies': ['warn', { max: 20 }],
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
    ],
    overrides: {
      '@intlify/vue-i18n/no-i18n-t-path-prop': 'error',
      '@intlify/vue-i18n/no-deprecated-i18n-component': 'error',
    },
  },
}, {
  files: ['**/src/**/*.@(ts|vue|js)'],
  rules: {
    'perfectionist/sort-objects': 'error',
  },
}, {
  files: ['**/src/**/*.ts'],
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
  },
}, {
  files: ['**/*'],
  rules: {
    'import/no-cycle': 'off',
  },
});

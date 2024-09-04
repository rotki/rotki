import path from 'node:path';
import rotki from '@rotki/eslint-config';

export default rotki({
  vue: {
    vueVersion: 3,
    overrides: {
      'vue/no-deprecated-model-definition': ['error'],
      'vue/no-deprecated-v-bind-sync': 'error',
    },
  },
  typescript: {
    tsconfigPath: 'tsconfig.json',
  },
  stylistic: true,
  rotki: {
    overrides: {
      '@rotki/no-deprecated-components': 'warn',
      '@rotki/no-deprecated-props': 'warn',
      '@rotki/no-legacy-library-import': 'warn',
      '@rotki/consistent-ref-type-annotation': ['error', {
        allowInference: true,
      }],
    },
  },
  cypress: {
    testDirectory: path.join('app', 'tests', 'e2e'),
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
  files: ['src/**/*.@(ts|vue|js)'],
  rules: {
    'perfectionist/sort-objects': 'error',
  },
}, {
  files: ['**/src/**/*.ts'],
  rules: {
    '@typescript-eslint/explicit-function-return-type': 'error',
  },
});

const path = require('node:path');
const rotki = require('@rotki/eslint-config').default;

module.exports = rotki({
  vue: {
    vueVersion: 3,
    overrides: {
      'vue/no-deprecated-model-definition': [
        'error',
      ],
      'vue/no-deprecated-v-bind-sync': 'error',
    },
  },
  typescript: {
    tsconfigPath: 'tsconfig.json',
  },
  stylistic: true,
  vuetify: {
    overrides: {
      'vuetify/no-deprecated-components': 'warn',
      'vuetify/no-deprecated-props': 'warn',
      'vuetify/no-deprecated-classes': 'off',
    },
  },
  rotki: {
    overrides: {
      '@rotki/no-deprecated-components': 'warn',
      '@rotki/no-deprecated-props': 'warn',
      '@rotki/no-legacy-library-import': 'warn',
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
});

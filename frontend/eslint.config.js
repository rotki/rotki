const path = require('node:path');
const rotki = require('@rotki/eslint-config').default;

module.exports = rotki({
  vue: {
    vueVersion: 2,
  },
  typescript: {
    tsconfigPath: 'tsconfig.json',
  },
  stylistic: true,
  vuetify: true,
  rotki: {
    overrides: {
      '@rotki/no-deprecated-components': ['warn', { legacy: true }],
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
  },
});

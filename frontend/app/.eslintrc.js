const path = require('node:path');

const srcDir = path.join(__dirname, 'src');
const localesDir = path.join(srcDir, 'locales');

module.exports = {
  extends: [
    './.eslintrc-auto-import.json',
    'plugin:@intlify/vue-i18n/recommended'
  ],
  rules: {
    '@intlify/vue-i18n/no-unused-keys': [
      'error',
      {
        extensions: ['.ts', '.vue'],
        ignores: [
          '/backend_mappings.*/',
          '/notification_messages.missing_api_key.*/',
          '/premium_components.*/',
          '/transactions.query_status.*/',
          '/transactions.query_status_events.*/',
          '/transactions.events.headers.*/'
        ]
      }
    ],
    '@intlify/vue-i18n/no-duplicate-keys-in-locale': 'error',
    '@intlify/vue-i18n/key-format-style': [
      'error',
      'snake_case',
      {
        allowArray: false
      }
    ],
    '@intlify/vue-i18n/no-raw-text': [
      process.env.NODE_ENV === 'development' ? 'warn' : 'error',
      {
        ignoreNodes: ['md-icon', 'v-icon', 'vicon'],
        ignorePattern: '^[-#:()&/+=!.]+$',
        ignoreText: ['EUR', 'HKD', 'USD']
      }
    ]
  },
  overrides: [
    {
      files: ['*.ts'],
      extends: ['@rotki/eslint-config-ts']
    },
    {
      files: ['src/**/*.vue'],
      extends: ['plugin:vuetify/recommended']
    }
  ],
  settings: {
    'vue-i18n': {
      localeDir: `${path.resolve(localesDir)}/*.{json,json5,yaml,yml}`,
      messageSyntaxVersion: '^9.0.0'
    }
  }
};

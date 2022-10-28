const path = require('path');

module.exports = {
  env: {
    node: true
  },

  plugins: ['vuetify'],

  extends: [
    'plugin:vue/recommended',
    'plugin:vue/essential',
    '@vue/typescript',
    'plugin:@intlify/vue-i18n/recommended',
    '@vue/prettier',
    './.eslintrc-auto-import.json'
  ],

  parser: 'vue-eslint-parser',

  rules: {
    'prettier/prettier': 'error',
    'vuetify/no-deprecated-classes': 'error',
    'vuetify/grid-unknown-attributes': 'error',
    'vuetify/no-legacy-grid': 'error',
    'vue/no-empty-component-block': 'error',
    'vue/multi-word-component-names': 'off',
    'vue/multiline-html-element-content-newline': [
      'error',
      {
        ignoreWhenEmpty: true,
        ignores: ['pre', 'textarea'],
        allowEmptyLines: false
      }
    ],
    'vue/v-bind-style': ['error', 'shorthand'],
    'vue/v-on-style': ['error', 'shorthand'],
    'vue/v-slot-style': [
      'error',
      {
        atComponent: 'shorthand',
        default: 'shorthand',
        named: 'shorthand'
      }
    ],
    'vue/component-name-in-template-casing': [
      'error',
      'kebab-case',
      {
        registeredComponentsOnly: false,
        ignores: []
      }
    ],
    'vue/no-static-inline-styles': [
      'error',
      {
        allowBinding: false
      }
    ],
    '@intlify/vue-i18n/key-format-style': [
      'error',
      'snake_case',
      {
        allowArray: false
      }
    ],
    '@intlify/vue-i18n/no-duplicate-keys-in-locale': 'error',
    '@intlify/vue-i18n/no-unused-keys': [
      'error',
      {
        src: './src',
        extensions: ['.ts', '.vue'],
        ignores: ['/transactions.query_status.*/', '/premium_components.*/']
      }
    ],
    '@intlify/vue-i18n/no-raw-text': [
      process.env.NODE_ENV === 'development' ? 'warn' : 'error',
      {
        ignoreNodes: ['md-icon', 'v-icon'],
        ignorePattern: '^[-#:()&/+]+$',
        ignoreText: ['EUR', 'HKD', 'USD']
      }
    ],
    'vue/html-self-closing': [
      'error',
      {
        html: {
          void: 'always',
          normal: 'always',
          component: 'always'
        },
        svg: 'always',
        math: 'always'
      }
    ],
    'vue/valid-v-slot': [
      'error',
      {
        allowModifiers: true
      }
    ],
    // vue 3 migration rules
    'vue/component-api-style': ['error', ['script-setup']],
    'vue/no-deprecated-dollar-listeners-api': 'error',
    'vue/no-deprecated-events-api': 'error',
    'vue/no-deprecated-filter': 'error',
    'vue/prefer-import-from-vue': 'error',
    'vue/require-explicit-emits': 'error',
    // cyclic imports
    'import/no-cycle': 'error'
  },

  parserOptions: {
    parser: '@typescript-eslint/parser',
    project: './tsconfig.eslint.json',
    sourceType: 'module',
    extraFileExtensions: ['.vue']
  },
  overrides: [
    {
      files: ['*.json'],
      rules: {
        '@typescript-eslint/naming-convention': 'off',
        '@typescript-eslint/no-floating-promises': 'off'
      }
    },
    {
      files: ['src/locales/**/*.json'],
      rules: {
        'jsonc/sort-keys': [
          'error',
          'asc',
          {
            caseSensitive: true,
            natural: false,
            minKeys: 2
          }
        ]
      },
      parser: 'jsonc-eslint-parser',
      extends: ['plugin:jsonc/recommended-with-json']
    },
    {
      files: ['*.json', '*.json5'],
      extends: ['plugin:@intlify/vue-i18n/base']
    },
    {
      files: ['*.yaml', '*.yml'],
      extends: ['plugin:@intlify/vue-i18n/base']
    }
  ],

  settings: {
    'vue-i18n': {
      localeDir:
        path.resolve(__dirname, 'src', 'locales') + '/*.{json,json5,yaml,yml}',
      messageSyntaxVersion: '^9.0.0'
    }
  }
};

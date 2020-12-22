const path = require('path');
const rulesDirPlugin = require('eslint-plugin-rulesdir');

rulesDirPlugin.RULES_DIR = path.resolve(__dirname, 'eslint/rules');

module.exports = {
  root: true,

  env: {
    node: true
  },

  plugins: ['vuetify', 'rulesdir', 'import'],

  extends: [
    'plugin:vue/recommended',
    'plugin:vue/essential',
    'eslint:recommended',
    '@vue/prettier',
    '@vue/prettier/@typescript-eslint',
    '@vue/typescript',
    'plugin:import/errors',
    'plugin:import/warnings',
    'plugin:import/typescript',
    'plugin:@intlify/vue-i18n/recommended'
  ],

  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'vuetify/no-deprecated-classes': 'error',
    'vuetify/grid-unknown-attributes': 'error',
    'vuetify/no-legacy-grid': 'error',
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
    'no-unused-vars': 'off',
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        vars: 'all',
        args: 'after-used',
        ignoreRestSiblings: true,
        argsIgnorePattern: '^_'
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
    'no-else-return': 'error',
    eqeqeq: ['error', 'always'],
    'import/order': [
      'error',
      {
        groups: ['builtin', 'external', 'parent', 'sibling', 'index'],
        alphabetize: {
          order: 'asc',
          caseInsensitive: true
        },
        pathGroups: [
          {
            pattern: '@/**',
            group: 'external',
            position: 'after'
          }
        ]
      }
    ],
    'vue/no-static-inline-styles': [
      'error',
      {
        allowBinding: false
      }
    ],
    'rulesdir/no-unused-components': 'error',
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
        extensions: ['.ts', '.vue']
      }
    ],
    '@intlify/vue-i18n/no-raw-text': [
      'error',
      {
        ignoreNodes: ['md-icon', 'v-icon'],
        ignorePattern: '^[-#:()&]+$',
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
    ]
  },

  parserOptions: {
    parser: '@typescript-eslint/parser'
  },

  settings: {
    'import/resolver': {
      alias: {
        map: [['@', path.resolve(__dirname, 'src')]],
        extensions: ['.vue', '.ts', '.d.ts']
      }
    },
    'vue-i18n': {
      localeDir:
        path.resolve(__dirname, 'src', 'locales') + '/*.{json,json5,yaml,yml}'
    }
  }
};

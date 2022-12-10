const { defineConfig } = require('eslint-define-config');
const { getPackageInfoSync } = require('local-pkg');

const pkg = getPackageInfoSync('vue');
let vueVersion = pkg && pkg.version;
vueVersion = +(vueVersion && vueVersion[0]);
vueVersion = Number.isNaN(vueVersion) ? 3 : vueVersion;

module.exports = defineConfig({
  globals: {
    // Reactivity Transform
    $: 'readonly',
    $$: 'readonly',
    $ref: 'readonly',
    $shallowRef: 'readonly',
    $computed: 'readonly',
    $customRef: 'readonly',
    $toRef: 'readonly'
  },
  overrides: [
    {
      files: ['*.vue'],
      parser: 'vue-eslint-parser',
      extends: ['plugin:vuetify/recommended'],
      parserOptions: {
        parser: '@typescript-eslint/parser',
        extraFileExtensions: ['.vue'],
        ecmaFeatures: {
          jsx: true
        }
      },
      globals: {
        // script setup
        defineProps: 'readonly',
        defineEmits: 'readonly',
        defineExpose: 'readonly',
        withDefaults: 'readonly',

        // RFC: https://github.com/vuejs/rfcs/discussions/430
        defineOptions: 'readonly'
      },
      rules: {
        'no-undef': 'off'
      }
    },
    {
      files: ['*.js', '*.ts', '*.vue'],
      rules: {
        'max-len': [
          'error',
          {
            code: 120,
            ignoreUrls: true
          }
        ]
      }
    }
  ],
  extends: [
    vueVersion === 3 ? 'plugin:vue/vue3-recommended' : 'plugin:vue/recommended',
    '@rotki/eslint-config-ts'
  ],
  rules: {
    'vue/max-attributes-per-line': 'off',
    'vue/no-v-html': 'off',
    'vue/multi-word-component-names': 'off',
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

    // Reactivity Transform
    'vue/no-setup-props-destructure': 'off',
    // Vue 3 migration
    'vue/component-api-style': ['error', ['script-setup']],
    'vue/no-deprecated-dollar-listeners-api': 'error',
    'vue/no-deprecated-events-api': 'error',
    'vue/no-deprecated-filter': 'error',
    'vue/prefer-import-from-vue': 'error',
    'vue/require-explicit-emits': 'error',
    // Custom rules
    'vue/valid-v-slot': [
      'error',
      {
        allowModifiers: true
      }
    ],
    'vue/no-empty-component-block': 'error',
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
    ]
  }
});

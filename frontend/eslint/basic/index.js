const { defineConfig } = require('eslint-define-config');

module.exports = defineConfig({
  env: {
    es6: true,
    browser: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:eslint-comments/recommended',
    'plugin:jsonc/recommended-with-jsonc',
    'plugin:yml/standard',
    'plugin:markdown/recommended'
  ],
  ignorePatterns: [
    '*.min.*',
    'CHANGELOG.md',
    'dist',
    'lib',
    'LICENSE*',
    'output',
    'coverage',
    'temp',
    'packages-lock.json',
    'pnpm-lock.yaml',
    'yarn.lock',
    'fixtures',
    '__snapshots__',
    '!.github',
    '!.vitepress',
    '!.vscode'
  ],
  plugins: ['import', 'html', 'unicorn'],
  settings: {
    'import/resolver': {
      node: { extensions: ['.js', '.mjs', '.ts', '.d.ts'] }
    }
  },
  overrides: [
    {
      files: ['*.json', '*.json5', '*.jsonc', '*rc'],
      parser: 'jsonc-eslint-parser'
    },
    {
      files: ['package.json'],
      parser: 'jsonc-eslint-parser',
      rules: {
        'jsonc/sort-keys': [
          'error',
          {
            pathPattern: '^$',
            order: [
              'name',
              'version',
              'private',
              'packageManager',
              'description',
              'type',
              'keywords',
              'license',
              'homepage',
              'bugs',
              'repository',
              'author',
              'contributors',
              'funding',
              'files',
              'main',
              'module',
              'types',
              'exports',
              'unpkg',
              'jsdelivr',
              'browser',
              'bin',
              'man',
              'directories',
              'publishConfig',
              'scripts',
              'peerDependencies',
              'peerDependenciesMeta',
              'optionalDependencies',
              'dependencies',
              'devDependencies',
              'engines',
              'config',
              'overrides',
              'pnpm',
              'husky',
              'lint-staged',
              'eslintConfig'
            ]
          },
          {
            pathPattern: '^(?:dev|peer|optional|bundled)?[Dd]ependencies$',
            order: { type: 'asc' }
          }
        ]
      }
    },
    {
      files: ['**/scripts/**/*.*', 'cli.*'],
      rules: {
        'no-console': 'off'
      }
    },
    {
      files: ['*.test.ts', '*.test.js', '*.spec.ts', '*.spec.js'],
      rules: {
        'no-unused-expressions': 'off'
      }
    },
    {
      // Code blocks in markdown file
      files: ['**/*.md/*.*'],
      rules: {
        '@typescript-eslint/no-redeclare': 'off',
        '@typescript-eslint/no-unused-vars': 'off',
        '@typescript-eslint/no-use-before-define': 'off',
        '@typescript-eslint/no-var-requires': 'off',
        'no-alert': 'off',
        'no-console': 'off',
        'no-restricted-imports': 'off',
        'no-undef': 'off',
        'no-unused-expressions': 'off',
        'no-unused-vars': 'off'
      }
    }
  ],
  rules: {
    // import
    'import/first': 'error',
    'import/no-mutable-exports': 'error',
    'import/no-duplicates': 'error',
    'import/no-cycle': 'error',
    'import/order': [
      'error',
      {
        groups: [
          'builtin',
          'external',
          'internal',
          'parent',
          'sibling',
          'index',
          'object',
          'type'
        ],
        pathGroups: [{ pattern: '@/**', group: 'internal' }],
        pathGroupsExcludedImportTypes: ['type']
      }
    ],

    // Common
    'no-unused-vars': 'warn',
    'no-constant-condition': 'warn',
    'no-debugger': 'warn',
    'no-console': ['warn', { allow: ['warn', 'error'] }],
    'no-restricted-syntax': [
      'error',
      // 'ForInStatement', TODO: Enable in the future
      'LabeledStatement',
      'WithStatement'
    ],
    // 'no-return-await': 'warn', TODO: Enable in the future
    'no-empty': ['error', { allowEmptyCatch: true }],
    'sort-imports': [
      'error',
      {
        ignoreCase: false,
        ignoreDeclarationSort: true,
        ignoreMemberSort: false,
        memberSyntaxSortOrder: ['none', 'all', 'multiple', 'single'],
        allowSeparatedGroups: false
      }
    ],

    // es6
    'no-var': 'error',
    'prefer-const': [
      'warn',
      { destructuring: 'all', ignoreReadBeforeAssign: true }
    ],
    'prefer-arrow-callback': [
      'error',
      { allowNamedFunctions: false, allowUnboundThis: true }
    ],
    'object-shorthand': [
      'error',
      'always',
      { ignoreConstructors: false, avoidQuotes: true }
    ],
    'prefer-rest-params': 'error',
    'prefer-spread': 'error',
    'prefer-template': 'error',
    //'require-await': 'error', TODO: enable as a warning initially

    // best-practice
    'array-callback-return': 'error',
    'block-scoped-var': 'error',
    eqeqeq: ['error', 'smart'],
    'no-alert': 'warn',
    'no-case-declarations': 'error',
    'no-fallthrough': ['warn', { commentPattern: 'break[\\s\\w]*omitted' }],
    'no-multi-str': 'error',
    'no-with': 'error',
    'no-void': 'error',

    // stylistic-issues
    'no-lonely-if': 'error',
    'no-else-return': 'error',
    'prefer-exponentiation-operator': 'error',

    // unicorns
    'unicorn/better-regex': 'error',
    'unicorn/custom-error-definition': 'error',
    'unicorn/error-message': 'error',
    'unicorn/escape-case': 'error',
    'unicorn/explicit-length-check': 'error',
    'unicorn/import-index': 'error',
    'unicorn/new-for-builtins': 'error',
    //'unicorn/no-array-callback-reference': 'error', TODO: enable as a warning
    'unicorn/no-array-method-this-argument': 'error',
    'unicorn/no-array-push-push': 'error',
    'unicorn/no-console-spaces': 'error',
    'unicorn/no-for-loop': 'error',
    'unicorn/no-hex-escape': 'error',
    'unicorn/no-instanceof-array': 'error',
    'unicorn/no-invalid-remove-event-listener': 'error',
    'unicorn/no-lonely-if': 'error',
    // 'unicorn/no-new-array': 'error', TODO: revaluate in the future
    'unicorn/no-new-buffer': 'error',
    'unicorn/no-unsafe-regex': 'off',
    'unicorn/number-literal-case': 'error',
    // 'unicorn/prefer-add-event-listener': 'error', TODO: enable later
    'unicorn/prefer-array-find': 'error',
    'unicorn/prefer-array-flat-map': 'error',
    'unicorn/prefer-array-index-of': 'error',
    'unicorn/prefer-array-some': 'error',
    'unicorn/prefer-date-now': 'error',
    // 'unicorn/prefer-dom-node-append': 'error',
    // 'unicorn/prefer-dom-node-dataset': 'error', requires es2022
    // 'unicorn/prefer-dom-node-remove': 'error',
    'unicorn/prefer-dom-node-text-content': 'error',
    'unicorn/prefer-includes': 'error',
    'unicorn/prefer-keyboard-event-key': 'error',
    'unicorn/prefer-math-trunc': 'error',
    'unicorn/prefer-modern-dom-apis': 'error',
    'unicorn/prefer-negative-index': 'error',
    'unicorn/prefer-node-protocol': 'error',
    // 'unicorn/prefer-number-properties': 'error', TODO: enable later
    'unicorn/prefer-optional-catch-binding': 'error',
    'unicorn/prefer-prototype-methods': 'error',
    // 'unicorn/prefer-query-selector': 'error', TODO: enable later
    'unicorn/prefer-reflect-apply': 'error',
    // 'unicorn/prefer-string-replace-all': 'error', TODO: enable later
    // 'unicorn/prefer-string-slice': 'error', TODO: enable later
    'unicorn/prefer-string-starts-ends-with': 'error',
    'unicorn/prefer-string-trim-start-end': 'error',
    'unicorn/prefer-type-error': 'error',
    'unicorn/throw-new-error': 'error',

    'eslint-comments/disable-enable-pair': 'off',

    'jsonc/quote-props': 'off',
    'jsonc/quotes': 'off',

    'yml/no-empty-mapping-value': 'off'
  }
});

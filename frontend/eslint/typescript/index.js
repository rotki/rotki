const fs = require('node:fs');
const { join } = require('node:path');
const { defineConfig } = require('eslint-define-config');
const basic = require('@rotki/eslint-config-basic');

module.exports = defineConfig({
  extends: [
    '@rotki/eslint-config-basic',
    'plugin:@typescript-eslint/recommended'
  ],
  ignorePatterns: ['auto-import.d.ts', 'components.d.ts'],
  overrides: basic.overrides
    .concat([
      {
        files: ['*.ts'],
        rules: {
          'no-undef': 'off',
          'max-lines': [
            'warn',
            {
              max: 400
            }
          ]
        }
      },
      {
        files: ['*.d.ts'],
        rules: {
          'import/no-duplicates': 'off'
        }
      },
      {
        files: ['*.js', '*.cjs'],
        rules: {
          '@typescript-eslint/no-var-requires': 'off'
        }
      },
      {
        files: ['.eslintrc.js'],
        extends: ['@rotki/eslint-config-basic']
      },
      {
        files: ['vite.config*.ts'],
        rules: {
          'no-console': 'off'
        }
      }
    ])
    .concat(
      !fs.existsSync(join(process.cwd(), 'tsconfig.eslint.json'))
        ? []
        : [
            {
              parserOptions: {
                tsconfigRootDir: process.cwd(),
                project: ['tsconfig.eslint.json']
              },
              parser: '@typescript-eslint/parser',
              excludedFiles: ['**/*.md/*.*'],
              files: ['*.ts', '*.tsx', '*.mts', '*.cts'],
              rules: {
                'no-throw-literal': 'off',
                '@typescript-eslint/no-throw-literal': 'error',
                'no-implied-eval': 'off',
                '@typescript-eslint/no-implied-eval': 'error',
                'dot-notation': 'off',
                '@typescript-eslint/dot-notation': [
                  'error',
                  { allowKeywords: true }
                ],
                'no-void': ['error', { allowAsStatement: true }],
                '@typescript-eslint/no-floating-promises': [
                  'error',
                  { ignoreIIFE: true }
                ],
                // '@typescript-eslint/no-misused-promises': 'error', TODO: enable later
                '@typescript-eslint/naming-convention': [
                  'error',
                  {
                    selector: 'variable',
                    modifiers: ['destructured'],
                    format: null
                  },
                  {
                    selector: 'parameter',
                    format: ['camelCase'],
                    leadingUnderscore: 'allow'
                  },
                  {
                    selector: 'variable',
                    format: ['camelCase']
                  },
                  {
                    selector: 'variable',
                    modifiers: ['const'],
                    format: ['camelCase', 'UPPER_CASE', 'PascalCase']
                  },
                  {
                    selector: 'memberLike',
                    modifiers: ['private'],
                    format: ['camelCase'],
                    leadingUnderscore: 'allow'
                  },
                  {
                    selector: 'typeLike',
                    format: ['PascalCase']
                  }
                ]
              }
            }
          ]
    ),
  rules: {
    'import/named': 'off',

    'no-unused-vars': 'off',
    // handled by unused-imports/no-unused-imports
    '@typescript-eslint/no-unused-vars': 'off',
    'no-redeclare': 'off',
    '@typescript-eslint/no-redeclare': 'off',

    '@typescript-eslint/ban-ts-comment': 'off',
    '@typescript-eslint/ban-types': 'off',
    '@typescript-eslint/consistent-type-imports': [
      'error',
      { fixStyle: 'inline-type-imports', disallowTypeAnnotations: false }
    ],
    '@typescript-eslint/consistent-type-assertions': [
      'error',
      {
        assertionStyle: 'as',
        objectLiteralTypeAssertions: 'allow'
      }
    ],
    '@typescript-eslint/explicit-module-boundary-types': 'off',
    '@typescript-eslint/no-explicit-any': 'off',
    '@typescript-eslint/no-non-null-assertion': 'off',
    '@typescript-eslint/prefer-as-const': 'error',

    '@typescript-eslint/no-empty-function': 'off', //TODO: evaluate again

    // Imports
    'import/max-dependencies': [
      // TODO: Raise the severity to 'error'
      'warn',
      {
        max: 20,
        ignoreTypeImports: false
      }
    ]
  }
});

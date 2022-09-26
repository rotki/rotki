const path = require('path');

module.exports = {
  root: true,

  parser: '@typescript-eslint/parser',

  env: {
    node: true
  },

  plugins: ['import','@typescript-eslint'],

  extends: [
    'eslint:recommended',
    'plugin:import/errors',
    'plugin:import/warnings',
    'plugin:import/typescript',
    'prettier',
  ],

  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
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
        leadingUnderscore: "allow"
      },
      {
        selector: 'typeLike',
        format: ['PascalCase']
      }
    ],
    '@typescript-eslint/no-floating-promises': ['error', { ignoreIIFE: true }]
  },

  overrides: [
    {
      files: ['*.ts'],
      rules: {
        'import/max-dependencies': [
          // TODO: Raise the severity to 'error'
          'warn',
          {
            max: 20,
            ignoreTypeImports: false,
          }
        ],
        'max-len': [
          // TODO: Raise the severity to 'error'
          'warn',
          {
            code: 400
          }
        ],
      }
    }
  ],
  parserOptions: {
    parser: '@typescript-eslint/parser',
    project: './tsconfig.json'
  },

  settings: {
    'import/resolver': {
      alias: {
        map: [
          ['@', path.resolve(__dirname, 'app/src')],
          ['@/rotki/common', path.resolve(__dirname, 'common/src')]
        ],
        extensions: ['.vue', '.ts', '.d.ts']
      }
    }
  },
  ignorePatterns: ['**/common/lib/**/*.js']
};

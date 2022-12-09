const { defineConfig } = require('eslint-define-config');
const { rules: prettierRules } = require('eslint-config-prettier');

delete prettierRules['vue/html-self-closing'];

module.exports = defineConfig({
  extends: ['plugin:yml/prettier'],
  plugins: ['prettier'],
  rules: {
    ...prettierRules,
    'prettier/prettier': 'warn'
  },
  ignorePatterns: ['auto-imports.d.ts', 'components.d.ts']
});

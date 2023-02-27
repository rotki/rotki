const { defineConfig } = require('eslint-define-config');
const { rules: prettierRules } = require('eslint-config-prettier');

delete prettierRules['vue/html-self-closing'];
delete prettierRules['curly'];

module.exports = defineConfig({
  extends: ['plugin:yml/prettier'],
  plugins: ['prettier'],
  rules: {
    ...prettierRules,
    'prettier/prettier': 'error'
  },
  ignorePatterns: ['auto-imports.d.ts', 'components.d.ts']
});

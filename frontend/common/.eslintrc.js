module.exports = {
  parser: '@typescript-eslint/parser',

  rules: {
    "no-redeclare": "off"
  },

  parserOptions: {
    project: './tsconfig.eslint.json'
  },
};

module.exports = {
  plugins: ['cypress'],
  env: {
    mocha: true,
    'cypress/globals': true,
    node: true
  },
  rules: {
    strict: 'off'
  }
};

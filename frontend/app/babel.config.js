const { CODE_COVERAGE } = process.env;

const plugins = [
  '@babel/plugin-proposal-nullish-coalescing-operator',
  '@babel/plugin-proposal-optional-chaining'
];

if (CODE_COVERAGE === 'true') {
  plugins.push('istanbul');
}

module.exports = {
  presets: [
    ['@vue/cli-plugin-babel/preset', { useBuiltIns: 'entry', corejs: '3.6.4' }]
  ],
  plugins
};

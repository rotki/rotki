module.exports = {
  presets: [['@vue/app', { useBuiltIns: 'entry' }]],
  plugins: ['@babel/plugin-proposal-nullish-coalescing-operator'],
  env: {
    test: {
      presets: [
        [
          '@babel/preset-env',
          {
            targets: {
              node: 'current'
            },
            useBuiltIns: 'entry'
          }
        ]
      ]
    }
  }
};

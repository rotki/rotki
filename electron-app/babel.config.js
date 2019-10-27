module.exports = {
  presets: [['@vue/app', { useBuiltIns: 'entry' }]],
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

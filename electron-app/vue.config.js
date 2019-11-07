// vue.config.js
module.exports = {
  chainWebpack: config => {
    // GraphQL Loader
    config.module
      .rule('node')
      .test(/\.node$/)
      .use('node-loader')
      .loader('node-loader')
      .end();
  },
  configureWebpack: {
    devtool: 'source-map'
  },
  pluginOptions: {
    electronBuilder: {
      builderOptions: {
        appId: 'io.rotkehlchen',
        extraResources: [
          {
            from: '../rotkehlchen_py_dist',
            to: 'rotkehlchen_py_dist',
            filter: ['**/*']
          }
        ],
        mac: {
          category: 'public.app-category.finance',
          icon: 'src/assets/images/rotki.icns'
        },
        win: {
          target: 'nsis',
          icon: 'src/assets/images/rotki.ico'
        },
        linux: {
          target: ['AppImage'],
          icon: 'srs/assets/images/rotki_1024x1024.png',
          category: 'Finance'
        }
      }
    }
  }
};

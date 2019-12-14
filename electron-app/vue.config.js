// vue.config.js
module.exports = {
  chainWebpack: config => {
    if (process.env.NODE_ENV === 'production') {
      config.module
        .rule('node')
        .test(/\.node$/)
        .use('native-ext-loader')
        .loader('native-ext-loader')
        .end();
    } else {
      config.module
        .rule('node')
        .test(/\.node$/)
        .use('node-loader')
        .loader('node-loader')
        .end();
    }
  },
  configureWebpack: {
    devtool: 'source-map'
  },
  pluginOptions: {
    electronBuilder: {
      externals: ['zeromq'],
      outputDir: 'dist',
      builderOptions: {
        appId: 'com.rotki',
        publish: {
          provider: 'github',
          vPrefixedTagName: true
        },
        buildVersion: process.env.ROTKEHLCHEN_VERSION,
        artifactName:
          '${productName}-${platform}_${arch}-${buildVersion}.${ext}',
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
          target: ['portable'],
          icon: 'src/assets/images/rotki.ico'
        },
        linux: {
          target: ['AppImage', 'tar.xz'],
          icon: 'srs/assets/images/rotki_1024x1024.png',
          category: 'Finance'
        }
      }
    }
  }
};

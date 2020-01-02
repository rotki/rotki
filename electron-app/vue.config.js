// vue.config.js
module.exports = {
  configureWebpack: {
    devtool: 'source-map'
  },
  pluginOptions: {
    electronBuilder: {
      outputDir: 'dist',
      builderOptions: {
        appId: 'com.rotki',
        publish: {
          provider: 'github',
          vPrefixedTagName: true,
          releaseType: 'draft'
        },
        buildVersion: process.env.ROTKEHLCHEN_VERSION,
        artifactName:
          '${productName}-${platform}_${arch}-v${buildVersion}.${ext}',
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
        },
        appImage: {
          publish: null
        }
      }
    }
  }
};

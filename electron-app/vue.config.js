// vue.config.js
module.exports = {
  configureWebpack: config => {
    if (
      process.env.NODE_ENV === 'development' ||
      process.env.CODE_COVERAGE === 'true'
    ) {
      config.devtool = 'eval-source-map';
      config.output.devtoolFallbackModuleFilenameTemplate =
        'webpack:///[resource-path]?[hash]';
      config.output.devtoolModuleFilenameTemplate = info => {
        const isVue = info.resourcePath.match(/\.vue$/);
        const isScript = info.query.match(/type=script/);
        const hasModuleId = info.moduleId !== '';

        // Detect generated files, filter as webpack-generated
        if (
          // Must result from vue-loader
          isVue &&
          // Must not be 'script' files (enough for chrome), or must have moduleId (firefox)
          (!isScript || hasModuleId)
        ) {
          let pathParts = info.resourcePath.split('/');
          const baseName = pathParts[pathParts.length - 1];
          // prepend 'generated-' to filename as well, so it's easier to find desired files via Ctrl+P
          pathParts.splice(-1, 1, `generated-${baseName}`);
          return `webpack-generated:///${pathParts.join('/')}?${info.hash}`;
        }

        // If not generated, filter as webpack-vue
        return `webpack-vue:///${info.resourcePath}`;
      };
    }
  },
  pluginOptions: {
    electronBuilder: {
      outputDir: 'dist',
      chainWebpackMainProcess: config => {
        // This makes sure that preload.ts is compiled along background.ts
        config.entry('preload').add('./src/preload.ts').end();
      },
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
          identity: false,
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

// vue.config.js
const { totalmem } = require('os');
const { DefinePlugin } = require('webpack');
const { ContextReplacementPlugin } = require('webpack');

module.exports = {
  devServer: {
    progress: false
  },
  productionSourceMap: false,
  chainWebpack: config => {
    config.plugin('fork-ts-checker').tap(args => {
      const systemMemory = Math.floor(totalmem() / 1024 / 1024);
      args[0].memoryLimit = systemMemory < 4 * 1024 ? systemMemory * 0.5 : 2048;
      return args;
    });
  },
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
    const appPackage = require('./package.json');
    const version = appPackage.version ?? '0.0.0';
    config.plugins.push(
      new DefinePlugin({
        'process.env': {
          VERSION: `'${version}'`
        }
      }),
      new ContextReplacementPlugin(/moment[/\\]locale$/, /en/)
    );
  },
  pluginOptions: {
    electronBuilder: {
      outputDir: 'dist',
      chainWebpackMainProcess: config => {
        // This makes sure that preload.ts is compiled along background.ts
        config.entry('preload').add('./src/preload.ts').end();
      },
      builderOptions: {
        appId: 'com.rotki.app',
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
            from: '../../rotkehlchen_py_dist',
            to: 'rotkehlchen_py_dist',
            filter: ['**/*']
          }
        ],
        dmg: {
          sign: false
        },
        nsis: {
          license: '../../LICENSE.md',
          createDesktopShortcut: false
        },
        mac: {
          category: 'public.app-category.finance',
          icon: 'src/assets/images/rotki.icns',
          ...(process.env.CI
            ? {
                identity: 'Rotki Solutions GmbH (6H86XUVS7L)',
                hardenedRuntime: true,
                gatekeeperAssess: false,
                entitlements: 'signing/entitlements.mac.plist',
                entitlementsInherit: 'signing/entitlements.mac.plist'
              }
            : {
                identity: false
              })
        },
        win: {
          target: ['nsis'],
          icon: 'src/assets/images/rotki.ico'
        },
        linux: {
          target: ['AppImage', 'tar.xz', 'deb'],
          icon: 'srs/assets/images/rotki_1024x1024.png',
          category: 'Finance'
        },
        ...(process.env.CI ? { afterSign: 'scripts/notarize.js' } : {})
      }
    },
    i18n: {
      locale: 'en',
      fallbackLocale: 'en',
      localeDir: 'locales',
      enableInSFC: true
    }
  },
  pwa: {
    workboxPluginMode: 'InjectManifest',
    workboxOptions: {
      swSrc: './src/sw.js',
      swDest: 'service-worker.js'
    }
  }
};

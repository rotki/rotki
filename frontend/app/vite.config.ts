import type { ComponentResolver } from 'unplugin-vue-components';
import { builtinModules } from 'node:module';
import path, { join, resolve } from 'node:path';
import process from 'node:process';
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import { VueRouterAutoImports } from 'unplugin-vue-router';
import VueRouter from 'unplugin-vue-router/vite';
import checker from 'vite-plugin-checker';
import istanbul from 'vite-plugin-istanbul';
import vueDevTools from 'vite-plugin-vue-devtools';
import { defineConfig } from 'vitest/config';

const PACKAGE_ROOT = __dirname;
const envPath = process.env.VITE_PUBLIC_PATH;
const publicPath = envPath || '/';
const isDevelopment = process.env.NODE_ENV === 'development';
const isCypress = !!process.env.VITE_CYPRESS;
const isTest = !!process.env.VITE_TEST;
const hmrEnabled = isDevelopment && !(process.env.CI && isTest);

function RuiComponentResolver(): ComponentResolver {
  return {
    type: 'component',
    resolve: (name: string) => {
      const prefix = 'Rui';
      if (name.startsWith(prefix)) {
        return {
          name,
          from: '@rotki/ui-library/components',
        };
      }
    },
  };
}

if (isTest)
  console.log('Running in test mode. Enabling Coverage');

if (envPath)
  console.log(`A custom publicPath has been specified, using ${envPath}`);

if (!hmrEnabled)
  console.info('HMR is disabled');

const enableChecker = !(process.env.CI || isTest || process.env.VITEST);

/**
 * These modules are required by walletconnect/appkit
 */
const requiredModules = ['buffer', 'events', 'crypto'] as const;

function isNotRequired(module: string): boolean {
  return !Array.prototype.includes.call(requiredModules, module);
}

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(PACKAGE_ROOT, 'src'),
      '~@': resolve(PACKAGE_ROOT, 'src'),
      '@shared': `${join(PACKAGE_ROOT, 'shared')}/`,
    },
    dedupe: ['vue'],
  },
  base: publicPath,
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
  optimizeDeps: {
    include: [
      'imask',
      'vanilla-jsoneditor',
      '@reown/appkit',
      '@reown/appkit/vue',
      '@reown/appkit/networks',
      '@reown/appkit-adapter-ethers',
      '@reown/walletkit',
      '@walletconnect/core',
      '@walletconnect/jsonrpc-utils',
      '@walletconnect/utils',
      'ethers',
    ],
  },
  plugins: [
    VueRouter({
      importMode: 'async',
    }),
    vue(),
    checker(enableChecker
      ? {
          vueTsc: {
            tsconfigPath: 'tsconfig.app.json',
          },
        }
      : {}),
    AutoImport({
      include: [
        /\.[jt]sx?$/, // .ts, .tsx, .js, .jsx
        /\.vue$/,
        /\.vue\?vue/, // .vue
        /\.md$/, // .md
      ],
      imports: [
        'vue',
        '@vueuse/core',
        '@vueuse/math',
        'pinia',
        { '@vueuse/shared': ['get', 'set'] },
        VueRouterAutoImports,
        {
          'vue-i18n': ['useI18n'],
        },
        {
          '@rotki/ui-library': ['useRotkiTheme', 'useBreakpoint', 'contextColors'],
        },
      ],
      dts: './auto-imports.d.ts',
      vueTemplate: true,
      injectAtEnd: true,
    }),
    Components({
      dts: true,
      include: [],
      dirs: [],
      resolvers: [RuiComponentResolver()],
      types: [
        {
          from: 'vue-router',
          names: ['RouterLink', 'RouterView'],
        },
      ],
    }),
    VueI18nPlugin({
      include: [path.resolve(__dirname, './src/locales/**')],
    }),
    ...(!isTest && process.env.ENABLE_DEV_TOOLS ? [vueDevTools()] : []),
    ...(isCypress
      ? [
          istanbul({
            include: 'src/*',
            exclude: ['node_modules', 'tests/', '**/*.d.ts'],
            extension: ['.ts', '.vue'],
            forceBuildInstrument: true,
          }),
        ]
      : []),
  ],
  server: {
    port: 8080,
    hmr: hmrEnabled,
    watch: {
      ignored: ['**/.e2e/**', '**/.nyc_output/**'],
    },
  },
  build: {
    sourcemap: isDevelopment || isTest,
    outDir: 'dist',
    assetsDir: '.',
    minify: true,
    rollupOptions: {
      external: [
        'electron',
        ...builtinModules.filter(isNotRequired).flatMap(p => [p, `node:${p}`]),
      ],
      input: join(PACKAGE_ROOT, 'index.html'),
      output: {
        chunkFileNames: (assetInfo: { name: string }) => {
          const currentName = assetInfo.name;
          const name = currentName.endsWith('.vue_vue_type_style_index_0_lang')
            || currentName.endsWith('.vue_vue_type_script_setup_true_lang')
            ? currentName.split('.')[0]
            : currentName;
          return `${name}-[hash].js`;
        },
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia', 'vue-i18n'],
          'common': ['@rotki/common', 'bignumber.js'],
          'ui-vendor': ['@rotki/ui-library'],
          'chart': ['chart.js', 'chartjs-plugin-zoom'],
          'editor': ['vanilla-jsoneditor'],
          'utils': [
            '@vueuse/math',
            '@vueuse/core',
            '@vueuse/shared',
            '@vuelidate/core',
            '@vuelidate/validators',
            'axios',
            'es-toolkit',
            'imask',
            'dayjs',
            'consola',
            'zod',
          ],
          'wallet-connect': [
            '@reown/walletkit',
            '@reown/appkit',
            '@reown/appkit-adapter-ethers',
            '@walletconnect/core',
          ],
        },
      },
    },
    emptyOutDir: false,
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern',
      },
    },
  },
});

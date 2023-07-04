import { builtinModules } from 'node:module';
import { join, resolve } from 'node:path';
import vue from '@vitejs/plugin-vue2';
import AutoImport from 'unplugin-auto-import/vite';
import DefineOptions from 'unplugin-vue-define-options/vite';
import { VuetifyResolver } from 'unplugin-vue-components/resolvers';
import Components from 'unplugin-vue-components/vite';
import { defineConfig } from 'vitest/config';
import { splitVendorChunkPlugin } from 'vite';
import { checker } from 'vite-plugin-checker';
import istanbul from 'vite-plugin-istanbul';
import { VitePWA } from 'vite-plugin-pwa';
import Layouts from 'vite-plugin-vue-layouts';

const PACKAGE_ROOT = __dirname;
const envPath = process.env.VITE_PUBLIC_PATH;
const publicPath = envPath ? envPath : '/';
const isDevelopment = process.env.NODE_ENV === 'development';
const isTest = !!process.env.VITE_TEST;
const hmrEnabled = isDevelopment && !(process.env.CI && isTest);

if (isTest) {
  console.log('Running in test mode. Enabling Coverage');
}

if (envPath) {
  console.log(`A custom publicPath has been specified, using ${envPath}`);
}

if (!hmrEnabled) {
  console.info('HMR is disabled');
}

export default defineConfig({
  resolve: {
    alias: {
      '@': resolve(PACKAGE_ROOT, 'src'),
      '~@': resolve(PACKAGE_ROOT, 'src')
    },
    dedupe: ['vue']
  },
  test: {
    globals: true,
    environment: 'jsdom',
    deps: {
      inline: ['vuetify']
    },
    setupFiles: ['tests/unit/setup-files/setup.ts'],
    coverage: {
      provider: 'v8',
      reportsDirectory: 'tests/unit/coverage',
      reporter: ['json'],
      include: ['src/*'],
      exclude: ['node_modules', 'tests/', '**/*.d.ts']
    }
  },
  base: publicPath,
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version)
  },
  plugins: [
    splitVendorChunkPlugin(),
    vue(),
    checker({
      vueTsc: !(process.env.CI || process.env.VITE_TEST || process.env.VITEST)
    }),
    AutoImport({
      imports: [
        'vue',
        'vue/macros',
        '@vueuse/core',
        '@vueuse/math',
        'pinia',
        { '@vueuse/shared': ['get', 'set'] },
        {
          'vue-router/composables': [
            'useRoute',
            'useRouter',
            'useLink',
            'onBeforeRouteUpdate',
            'onBeforeRouteLeave'
          ]
        }
      ],
      dts: 'src/auto-imports.d.ts',
      dirs: [
        'src/composables/**',
        'src/api/**',
        'src/store/**',
        'src/utils/**'
      ],
      vueTemplate: true,
      eslintrc: {
        enabled: true
      }
    }),
    Components({
      dts: true,
      include: [/\.vue$/, /\.vue\?vue/],
      resolvers: [VuetifyResolver()],
      types: [
        {
          from: 'vue-router',
          names: ['RouterLink', 'RouterView']
        }
      ]
    }),
    DefineOptions(),
    Layouts({
      layoutsDirs: ['src/layouts'],
      defaultLayout: 'default'
    }),
    ...(isTest
      ? [
          istanbul({
            include: 'src/*',
            exclude: ['node_modules', 'tests/', '**/*.d.ts'],
            extension: ['.ts', '.vue']
          })
        ]
      : []),
    VitePWA({
      base: publicPath,
      registerType: 'prompt',
      manifest: false
    })
  ],
  server: {
    port: 8080,
    hmr: hmrEnabled,
    watch: {
      ignored: ['**/.e2e/**', '**/.nyc_output/**']
    }
  },
  build: {
    sourcemap: isDevelopment || isTest,
    outDir: 'dist',
    assetsDir: '.',
    minify: true,
    rollupOptions: {
      external: [
        'electron',
        'electron-devtools-installer',
        ...builtinModules.flatMap(p => [p, `node:${p}`])
      ],
      input: join(PACKAGE_ROOT, 'index.html')
    },
    emptyOutDir: false
  }
});

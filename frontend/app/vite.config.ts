import type { ComponentResolver } from 'unplugin-vue-components';
import { builtinModules } from 'node:module';
import { join, relative, resolve } from 'node:path';
import process from 'node:process';
import VueI18nPlugin from '@intlify/unplugin-vue-i18n/vite';
import { ruiIconsPlugin } from '@rotki/ui-library/vite-plugin';
import vue from '@vitejs/plugin-vue';
import AutoImport from 'unplugin-auto-import/vite';
import Components from 'unplugin-vue-components/vite';
import { createLogger, type Logger, type LogOptions, type Plugin } from 'vite';
import checker from 'vite-plugin-checker';
import vueDevTools from 'vite-plugin-vue-devtools';
import { defineConfig } from 'vitest/config';
import { VueRouterAutoImports } from 'vue-router/unplugin';
import VueRouter from 'vue-router/vite';
import { backendIcons } from './backend-icons.generated';
import { backendIconsCachePlugin } from './scripts/extract-backend-icons';

const PACKAGE_ROOT = __dirname;
const PROJECT_ROOT = resolve(PACKAGE_ROOT, '../..');

/**
 * Under `pnpm dev` the process forwarder already prefixes every line with its own
 * `<label> <time>`, so Vite's own `timestamp: true` logs (HMR/client messages)
 * would print a second clock. When forwarded, wrap the default logger to force
 * `timestamp: false`; standalone `vite` runs keep their timestamps.
 */
function createConfigLogger(): Logger | undefined {
  if (process.env.ROTKI_DEV_FORWARDED !== '1')
    return undefined;

  const base = createLogger();
  const noTimestamp = (options?: LogOptions): LogOptions => ({ ...options, timestamp: false });
  return {
    ...base,
    error: (msg, options): void => base.error(msg, noTimestamp(options)),
    info: (msg, options): void => base.info(msg, noTimestamp(options)),
    warn: (msg, options): void => base.warn(msg, noTimestamp(options)),
    warnOnce: (msg, options): void => base.warnOnce(msg, noTimestamp(options)),
  };
}

const envPath = process.env.VITE_PUBLIC_PATH;
const publicPath = envPath ?? '/';
const isDevelopment = process.env.NODE_ENV === 'development';
const isTest = !!process.env.VITE_TEST;
const isCoverage = !!process.env.VITE_COVERAGE;
const hmrEnabled = isDevelopment && !(process.env.CI && isTest);
// Single source of truth for the accounting-update feature: the backend gates its
// endpoints behind ROTKI_ACCOUNTING_UPDATE, so we mirror that same shell var into a
// VITE_-prefixed entry, which Vite then exposes on import.meta.env. Exporting the one
// var drives both backend and frontend with no drift and no separate frontend flag.
// We must match the backend's exact check (feature_flags.py: `== 'True'`) — copying
// the raw value would let e.g. `=1` enable the frontend while the backend stays off.
if (process.env.ROTKI_ACCOUNTING_UPDATE === 'True')
  process.env.VITE_ACCOUNTING_UPDATE = 'true';

/**
 * Force a full page reload when a locale JSON changes. @intlify/unplugin-vue-i18n
 * precompiles the messages and self-accepts the compiled module, so edits to
 * src/locales are silently swallowed (no reload, stale text) and an
 * `import.meta.hot.accept` + `setLocaleMessage` fallback no-ops. A full reload
 * re-fetches the recompiled messages and re-initialises i18n from scratch.
 */
function reloadOnLocaleChange(): Plugin {
  const localeDir = resolve(PACKAGE_ROOT, './src/locales');
  return {
    name: 'rotki:reload-on-locale-change',
    handleHotUpdate({ file, server }) {
      if (file.startsWith(localeDir) && file.endsWith('.json')) {
        server.config.logger.info(
          `[locale] ${relative(PACKAGE_ROOT, file)} changed, reloading page...`,
          { clear: true, timestamp: true },
        );
        server.ws.send({ path: '*', type: 'full-reload' });
        return [];
      }
    },
  };
}

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

const enableChecker = !((process.env.CI ?? isTest) || process.env.VITEST);

/**
 * These modules are required by walletconnect
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
  customLogger: createConfigLogger(),
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
  optimizeDeps: {
    include: [
      'imask',
      'vanilla-jsoneditor',
      '@walletconnect/core',
      '@walletconnect/universal-provider',
      'viem',
      'plainfp',
      'plainfp/result-async',
      'plainfp/option',
      'plainfp/pipe',
      'plainfp/brand',
      '@rotki/ui-library/components',
      'vue-echarts',
    ],
  },
  plugins: [
    backendIconsCachePlugin(PROJECT_ROOT),
    VueRouter({
      importMode: 'async',
      dts: './src/route-map.d.ts',
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
    ruiIconsPlugin({
      include: [
        ...backendIcons,
        // icons used by the components
        'lu-minus',
        'lu-message-square-quote',
        'lu-equal',
        'lu-map-pin-check-inside',
        'lu-square-kanban',
        'lu-corner-up-left',
        'lu-droplets',
        'lu-receipt-cent',
        'lu-deposits',
        'lu-liabilities',
        'lu-palette',
        'lu-slash',
        'lu-monitor',
      ],
      customIcons: ['lu-github', 'lu-discord', 'lu-x-twitter'],
    }),
    VueI18nPlugin({
      include: [resolve(PACKAGE_ROOT, './src/locales/**')],
    }),
    reloadOnLocaleChange(),
    ...(!isTest && process.env.ENABLE_DEV_TOOLS ? [vueDevTools()] : []),
  ],
  server: {
    port: 8080,
    hmr: hmrEnabled,
    watch: {
      ignored: [
        /[/\\]\.e2e[/\\]/,
        /\.spec\.ts$/,
        /[/\\]coverage[/\\]/,
        /[/\\]dist[/\\]/,
        /[/\\]build[/\\]/,
        /[/\\]\.nyc_output[/\\]/,
        /[/\\]\.contract[/\\]/,
        /[/\\]playwright-report[/\\]/,
        /[/\\]tests[/\\]e2e[/\\]/,
      ],
    },
  },
  build: {
    sourcemap: isDevelopment || isTest || isCoverage,
    outDir: 'dist',
    assetsDir: '.',
    minify: true,
    rolldownOptions: {
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
        manualChunks: (id: string): string | undefined => {
          const chunkGroups: Record<string, string[]> = {
            'vue-vendor': ['vue', 'vue-router', 'pinia', 'vue-i18n'],
            'common': ['@rotki/common', 'bignumber.js'],
            'ui-vendor': ['@rotki/ui-library'],
            'chart': ['echarts', 'vue-echarts'],
            'editor': ['vanilla-jsoneditor'],
            'utils': [
              '@vueuse/math',
              '@vueuse/core',
              '@vueuse/shared',
              '@vuelidate/core',
              '@vuelidate/validators',
              'ofetch',
              'es-toolkit',
              'imask',
              'dayjs',
              'consola',
              'zod',
            ],
            'wallet-connect': [
              '@walletconnect/core',
              '@walletconnect/universal-provider',
              'viem',
            ],
          };
          for (const [chunk, packages] of Object.entries(chunkGroups)) {
            if (packages.some(pkg => id.includes(`/node_modules/${pkg}/`))) {
              return chunk;
            }
          }
          return undefined;
        },
      },
    },
    emptyOutDir: false,
  },
});

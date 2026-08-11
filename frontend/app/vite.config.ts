import type { ComponentResolver } from 'unplugin-vue-components';
import { readFileSync } from 'node:fs';
import { builtinModules } from 'node:module';
import { join, resolve } from 'node:path';
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

// Read from the manifest instead of npm_package_version: the latter depends on how
// the process was launched and is the workspace root's version when it is not vite
// that pnpm invoked directly.
const appVersion: string = JSON.parse(readFileSync(join(PACKAGE_ROOT, 'package.json'), 'utf8')).version;

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

/**
 * Sharded e2e runs (`scripts/e2e-shards.ts`) serve ONE bundle from several `vite preview`
 * servers, one per shard. That only works because the bundle names no port: it is built
 * with an empty `VITE_BACKEND_URL`, so every call goes same-origin, and each preview
 * server forwards those calls to its own shard's starling proxy.
 *
 * The port is read when preview starts rather than when the bundle is built, which is
 * what lets one build serve every shard. `E2E_PORT_OFFSET` is the block the run settled
 * on and 30305 is the proxy inside it, matching playwright.config.ts.
 */
const E2E_BASE_PROXY_PORT = 30305;
const e2eShard = Number(process.env.E2E_SHARD ?? 0);
const e2eProxyTarget = `http://127.0.0.1:${E2E_BASE_PROXY_PORT + Number(process.env.E2E_PORT_OFFSET ?? 0)}`;
/**
 * The keys are anchored regexes, not plain prefixes, because the bundle's own chunks sit
 * at the root and are named after the module they came from: a bare `/api` key also
 * matches the `/api-<hash>.js` chunk, which is then forwarded to a backend that has
 * never heard of it. The 404 arrives as a failed dynamic import of the login chunk, and
 * the app renders a blank page with nothing in the console naming the proxy.
 */
const previewProxy = e2eShard > 0
  ? {
      '^/api/': { target: e2eProxyTarget },
      // Task and balance updates the backend pushes over a websocket.
      '^/ws/': { target: e2eProxyTarget, ws: true },
      // starling strips the prefix itself, so this is a plain forward.
      '^/colibri/': { target: e2eProxyTarget },
    }
  : undefined;
// Single source of truth for the accounting-update feature: the backend gates its
// endpoints behind ROTKI_ACCOUNTING_UPDATE, so we mirror that same shell var into a
// VITE_-prefixed entry, which Vite then exposes on import.meta.env. Exporting the one
// var drives both backend and frontend with no drift and no separate frontend flag.
// We must match the backend's exact check (feature_flags.py: `== 'True'`) — copying
// the raw value would let e.g. `=1` enable the frontend while the backend stays off.
if (process.env.ROTKI_ACCOUNTING_UPDATE === 'True')
  process.env.VITE_ACCOUNTING_UPDATE = 'true';

/**
 * Hot-swap locale messages instead of losing the app state on every en.json edit.
 *
 * Vite 8 no longer ships a JS `vite:json` plugin, so @intlify/unplugin-vue-i18n falls
 * back to its virtual-module path and serves each locale as `virtual:intlify-i18n-N`.
 * That path has no HMR wiring: the compiled module is cached and never invalidated, so
 * locale edits are invisible even across a full page reload until the dev server is
 * restarted. Invalidating those virtual modules here re-runs the message compiler and
 * lets the `import.meta.hot.accept` handler in src/i18n.ts swap the messages in place.
 */
function hmrLocaleMessages(): Plugin {
  const localeDir = resolve(PACKAGE_ROOT, './src/locales');
  const virtualPrefix = 'virtual:intlify-i18n-';
  return {
    name: 'rotki:hmr-locale-messages',
    hotUpdate({ file, modules }) {
      if (!file.startsWith(localeDir) || !file.endsWith('.json'))
        return;

      const graph = this.environment.moduleGraph;
      const virtualModules = [...graph.idToModuleMap.entries()]
        .filter(([id]) => id.startsWith(virtualPrefix))
        .map(([, mod]) => mod);

      for (const mod of virtualModules)
        graph.invalidateModule(mod);

      return [...modules, ...virtualModules];
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

// vue-tsc in the dev server is expensive (it type-checks the whole project on every
// change), so it is opt-in: set ENABLE_TYPE_CHECKER=1 when you want inline type errors.
// `pnpm run typecheck` remains the canonical check and CI runs it separately.
const enableChecker = !!process.env.ENABLE_TYPE_CHECKER && !((process.env.CI ?? isTest) || process.env.VITEST);

if (enableChecker)
  console.info('Type checker is enabled');

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
  preview: {
    proxy: previewProxy,
  },
  customLogger: createConfigLogger(),
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
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
    ...(enableChecker
      ? [checker({
          vueTsc: {
            tsconfigPath: 'tsconfig.app.json',
          },
        })]
      : []),
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
        // task-center activity outcomes: named in activity-outcome.ts, so the source scan of
        // templates never sees them (see the warning on `ActivityOutcome.icon`)
        'lu-activity',
        'lu-ban',
        'lu-check',
        'lu-circle-x',
        'lu-clock',
        'lu-skip-forward',
      ],
      customIcons: ['lu-github', 'lu-discord', 'lu-x-twitter'],
    }),
    VueI18nPlugin({
      include: [resolve(PACKAGE_ROOT, './src/locales/**')],
    }),
    hmrLocaleMessages(),
    // Opt-in and deliberately NOT tied to ENABLE_DEV_TOOLS (which only opens Electron's
    // Chrome DevTools, see electron/main/window-manager.ts): vite-plugin-vue-devtools
    // breaks Vue SFC hot reload, so every .vue edit needs a manual page reload while it
    // is installed. Enable it only when you actually need the Vue DevTools panel.
    ...(!isTest && process.env.ENABLE_VUE_DEVTOOLS ? [vueDevTools()] : []),
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

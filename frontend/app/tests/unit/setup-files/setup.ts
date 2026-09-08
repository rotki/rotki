import type { DatabaseInfo } from '@/modules/session/backup';
import process from 'node:process';
import { mockT } from '@test/i18n';
import { RuiAlertStub } from '@test/stubs/RuiAlert';
import { RuiAutoCompleteStub } from '@test/stubs/RuiAutoComplete';
import { RuiIconStub } from '@test/stubs/RuiIcon';
import { RuiTooltipStub } from '@test/stubs/RuiTooltip';
import { config, enableAutoUnmount } from '@vue/test-utils';
import consola, { type ConsolaReporter } from 'consola';
import { afterAll, afterEach, beforeAll, beforeEach, onTestFailed, vi } from 'vitest';
import { server } from './server';
import 'fake-indexeddb/auto';

/* Buffer the app logger per test and replay it only on failure, so passing tests stay quiet.
   Vue and MSW warnings go through console.* and are left visible. VITEST_VERBOSE=1 disables
   the buffering. */
if (!process.env.VITEST_VERBOSE) {
  type LogArgs = Parameters<ConsolaReporter['log']>;
  let capturedReporters: ConsolaReporter[] | undefined;
  let logBuffer: LogArgs[] = [];

  const bufferingReporter: ConsolaReporter = {
    log(...args): void {
      logBuffer.push(args);
    },
  };

  beforeEach((): void => {
    capturedReporters ??= consola.options.reporters.slice();
    logBuffer = [];
    consola.setReporters([bufferingReporter]);
    onTestFailed((): void => {
      for (const args of logBuffer) {
        for (const reporter of capturedReporters ?? [])
          reporter.log(...args);
      }
    });
  });
}

vi.mock('@/modules/assets/api/use-asset-info-api', () => ({
  useAssetInfoApi: vi.fn().mockReturnValue({
    assetMapping: vi.fn().mockResolvedValue({ assets: {}, assetCollections: {} }),
  }),
}));

vi.mock('@/modules/balances/api/use-price-api', () => ({
  usePriceApi: vi.fn().mockReturnValue({
    getPriceCache: vi.fn().mockResolvedValue([]),
    createPriceCache: vi.fn().mockResolvedValue({ taskId: 1 }),
    deletePriceCache: vi.fn().mockResolvedValue(true),
    queryHistoricalRate: vi.fn().mockResolvedValue({ taskId: 1 }),
    queryHistoricalRates: vi.fn().mockResolvedValue({ taskId: 1 }),
    queryFiatExchangeRates: vi.fn().mockResolvedValue({ taskId: 1 }),
    queryPrices: vi.fn().mockResolvedValue({ taskId: 1 }),
    queryCachedPrices: vi.fn().mockResolvedValue({}),
  }),
}));

vi.mock('@/modules/session/api/use-queried-address-api', () => ({
  useQueriedAddressApi: vi.fn().mockReturnValue({}),
}));

vi.mock('@/modules/session/api/use-backup-api', () => ({
  useBackupApi: vi.fn().mockReturnValue({
    info: vi.fn().mockReturnValue({
      userdb: {
        info: {
          filepath: '/dev/db.db',
          size: 1234,
          version: 5,
        },
        backups: [],
      },
      globaldb: {
        globaldbAssetsVersion: 1,
        globaldbSchemaVersion: 1,
      },
    } satisfies DatabaseInfo),
  }),
}));

vi.mock('@vueuse/core', async () => {
  const mod = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');

  return {
    ...mod,
    useElementBounding: vi.fn().mockReturnValue({ left: 0, right: 0, top: 0, bottom: 0 }),
    useFocus: vi.fn().mockReturnValue({ focused: ref(false) }),
    useResizeObserver: vi.fn().mockReturnValue({ stop: vi.fn() }),
    useVirtualList: vi.fn().mockImplementation((options: []) => ({
      containerProps: {
        ref: ref(),
        onScroll: vi.fn(),
      },
      list: computed(() => get(options).map((data, index) => ({ data, index }))),
      wrapperProps: {},
      scrollTo: vi.fn(),
    })),
  };
});

/* `@/i18n` builds the real instance from `locales/en.json`, ~835ms to import, and nothing in a
   unit test uses it. It is reached transitively from `@/message-key`, which every settings
   registry slice imports, so leaving it real taxes any spec that touches a setting. */
vi.mock('@/i18n', () => ({
  i18n: { global: { te: (): boolean => true } },
  loadLocaleMessages: vi.fn(async () => Promise.resolve()),
}));

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: mockT,
    te: mockT,
    locale: ref(''),
  }),
  createI18n: () => ({}),
}));

vi.mock('vue-router', () => {
  const route = ref({
    query: {},
  });

  return {
    useRoute: vi.fn().mockReturnValue(route),
    useRouter: vi.fn().mockImplementation(() => ({
      currentRoute: route,
      push: vi.fn(({ query }) => {
        set(route, { ...get(route), query });
        return true;
      }),
      // Components that clear a `?add=`-style parameter call replace, so the mock must expose it.
      replace: vi.fn(({ query }) => {
        set(route, { ...get(route), query });
        return true;
      }),
    })),
    createRouter: vi.fn().mockImplementation(() => ({
      beforeEach: vi.fn(),
    })),
    createWebHashHistory: vi.fn(),
    // The mocked push always succeeds, so nothing here is ever a navigation failure.
    isNavigationFailure: vi.fn().mockReturnValue(false),
  };
});

vi.mock('@/modules/shell/app/use-websocket-connection', () => ({
  useWebsocketConnection: () => ({
    connected: ref(false),
    connect: vi.fn(),
    disconnect: vi.fn(),
    setConnectionEnabled: vi.fn(),
  }),
}));

vi.mock('@/modules/shell/app/use-monitor-service', () => ({
  useMonitorService: () => ({
    restart: vi.fn(),
    start: vi.fn(),
    startTaskMonitoring: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock('@/modules/shell/app/use-backend-messages', () => ({
  useBackendMessages: () => ({
    isMacOsVersionUnsupported: ref(false),
    isWinVersionUnsupported: ref(false),
    registerOAuthCallbackHandler: vi.fn(),
    startupErrorMessage: ref(''),
    unregisterOAuthCallbackHandler: vi.fn(),
  }),
}));

vi.mock('@rotki/ui-library', async () => {
  const actual = await vi.importActual<typeof import('@rotki/ui-library')>('@rotki/ui-library');
  return {
    ...actual,
    createBlockie: vi.fn().mockImplementation(({ seed }) => `${seed.toLowerCase()}face`),
  };
});

/**
 * Fails a request to the backend that no handler covers, instead of letting it reach the network.
 *
 * @remarks
 * Under `warn` the message went to a console vitest silences for a passing test, so a component
 * querying from `onMounted` opened a real socket on every run and the suite still exited 0. The
 * error has to be thrown: `print.error` only reports, and the request proceeds regardless.
 *
 * Only the backend is guarded. A spec may start a server of its own and talk to it, which the
 * address import server spec does on an ephemeral port.
 */
function failUnhandledBackendRequest(request: Request, print: { error: () => void }): void {
  const backendUrl = process.env.VITE_BACKEND_URL;
  if (!backendUrl || !request.url.startsWith(backendUrl))
    return;

  print.error();
  throw new Error(`No msw handler for ${request.method} ${request.url}`);
}

beforeAll(() => {
  server.listen({
    onUnhandledRequest: failUnhandledBackendRequest,
  });

  class ResizeObserverMock {
    observe = vi.fn();
    unobserve = vi.fn();
    disconnect = vi.fn();
  }
  globalThis.ResizeObserver = ResizeObserverMock;
});

afterEach(() => server.resetHandlers());

afterAll(() => server.close());

/**
 * Drops the nodes a teleport left on `document.body`.
 *
 * @remarks
 * An overlay teleports out of the wrapper, so unmounting the wrapper does not reach it. A dialog or
 * menu left behind answers the next test's document query, which then passes having rendered
 * nothing of its own.
 *
 * This setup file is shared with the node-environment specs under `electron/` and `shared/`, which
 * have no document at all.
 */
function clearTeleportedNodes(): void {
  if (typeof document !== 'undefined')
    document.body.innerHTML = '';
}

afterEach(clearTeleportedNodes);

config.global.stubs.RuiAlert = RuiAlertStub;
config.global.stubs.RuiAutoComplete = RuiAutoCompleteStub;
config.global.stubs.RuiIcon = RuiIconStub;
config.global.stubs.RuiTooltip = RuiTooltipStub;
config.global.stubs.I18nT = true;
// JsonInput lazy-loads `vanilla-jsoneditor` on mount, and no spec asserts its DOM.
config.global.stubs.JsonInput = true;

// A leaked wrapper keeps reacting to module-level state during later tests.
enableAutoUnmount(afterEach);

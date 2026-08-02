import type { DatabaseInfo } from '@/modules/session/backup';
import process from 'node:process';
import { mockT } from '@test/i18n';
import { RuiAlertStub } from '@test/stubs/RuiAlert';
import { RuiAutoCompleteStub } from '@test/stubs/RuiAutoComplete';
import { RuiIconStub } from '@test/stubs/RuiIcon';
import { RuiTooltipStub } from '@test/stubs/RuiTooltip';
import { config } from '@vue/test-utils';
import consola, { type ConsolaReporter } from 'consola';
import { afterAll, afterEach, beforeAll, beforeEach, onTestFailed, vi } from 'vitest';
import { server } from './server';
import 'fake-indexeddb/auto';

// Consola (the app logger) noise control: buffer app log output per test and only
// replay it when that test fails. Passing tests stay quiet; failing tests keep
// their logs for debugging. Vue warnings and MSW warnings go through console.* and
// are intentionally left untouched so genuine issues stay visible and get fixed at
// the source. Set VITEST_VERBOSE=1 to disable buffering and see all logger output.
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

// `@/i18n` builds the real instance from `locales/en.json`, which costs ~835ms to import.
// Nothing in a unit test uses it: `createI18n` is already mocked below, no spec imports the
// module, and its only other consumer - the dev key-existence warning in `@/message-key` - is
// compiled out under MODE === 'test'. It is reached transitively though (message-key is imported
// by every settings registry slice), so leaving it real taxes any spec that touches a setting.
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

beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'warn',
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

// Global stub components
config.global.stubs.RuiAlert = RuiAlertStub;
config.global.stubs.RuiAutoComplete = RuiAutoCompleteStub;
config.global.stubs.RuiIcon = RuiIconStub;
config.global.stubs.RuiTooltip = RuiTooltipStub;
config.global.stubs.I18nT = true;
// JsonInput lazy-loads the heavy `vanilla-jsoneditor` on mount; no spec asserts its
// DOM, so stub it globally to keep form mounts fast.
config.global.stubs.JsonInput = true;

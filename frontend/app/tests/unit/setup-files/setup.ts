import type { DatabaseInfo } from '@/modules/session/backup';
import { mockT } from '@test/i18n';
import { RuiAlertStub } from '@test/stubs/RuiAlert';
import { RuiAutoCompleteStub } from '@test/stubs/RuiAutoComplete';
import { RuiIconStub } from '@test/stubs/RuiIcon';
import { RuiTooltipStub } from '@test/stubs/RuiTooltip';
import { config } from '@vue/test-utils';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { server } from './server';
import 'fake-indexeddb/auto';

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

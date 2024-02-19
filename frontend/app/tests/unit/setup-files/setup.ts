import { config } from '@vue/test-utils';
import { mockT } from '../i18n';
import RuiIconStub from '../specs/stubs/RuiIcon';
import RuiTooltipStub from '../specs/stubs/RuiTooltip';
import { server } from './server';

beforeAll(() => {
  server.listen({
    onUnhandledRequest: 'warn',
  });

  vi.mock('@/composables/api/assets/info', () => ({
    useAssetInfoApi: vi.fn().mockReturnValue({
      assetMapping: vi.fn().mockResolvedValue({}),
    }),
  }));

  vi.mock('@/composables/api/balances/price', () => ({
    usePriceApi: vi.fn().mockReturnValue({
      getPriceCache: vi.fn().mockResolvedValue([]),
      createPriceCache: vi.fn().mockResolvedValue(1),
      deletePriceCache: vi.fn().mockResolvedValue(1),
      queryHistoricalRate: vi.fn().mockResolvedValue(1),
      queryFiatExchangeRates: vi.fn().mockResolvedValue(1),
      queryPrices: vi.fn().mockResolvedValue(1),
    }),
  }));

  vi.mock('@/composables/api/session/queried-addresses', () => ({
    useQueriedAddressApi: vi.fn().mockReturnValue({}),
  }));

  vi.mock('@/composables/api/backup', () => ({
    useBackupApi: vi.fn().mockReturnValue({
      info: vi.fn().mockReturnValue({}),
    }),
  }));

  vi.mock('@vueuse/core', async () => {
    const mod = await vi.importActual<typeof import('@vueuse/core')>('@vueuse/core');

    return {
      ...mod,
      useElementBounding: vi
        .fn()
        .mockReturnValue({ left: 0, right: 0, top: 0, bottom: 0 }),
      useFocus: vi.fn().mockReturnValue({ focused: false }),
      useResizeObserver: vi.fn(),
    };
  });

  vi.mock('vue-i18n', async () => ({
    useI18n: () => ({
      t: mockT,
      te: mockT,
      locale: ref(''),
    }),
  }));

  vi.mock('@/store/websocket', () => ({
    useWebsocketStore: () => ({
      connected: ref(false),
      connect: vi.fn(),
      disconnect: vi.fn(),
    }),
  }));

  vi.mock('@/utils/blockie', () => ({
    createBlockie: vi
      .fn()
      .mockImplementation(({ seed }) => `${seed.toLowerCase()}face`),
  }));

  globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

afterEach(() => server.resetHandlers());

afterAll(() => server.close());

// Global stub components
config.global.stubs.RuiIcon = RuiIconStub;
config.global.stubs.RuiTooltip = RuiTooltipStub;

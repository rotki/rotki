import { config } from '@vue/test-utils';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { mockT } from '../i18n';
import { RuiIconStub } from '../specs/stubs/RuiIcon';
import { RuiTooltipStub } from '../specs/stubs/RuiTooltip';
import { RuiAutoCompleteStub } from '../specs/stubs/RuiAutoComplete';
import { server } from './server';
import type { DatabaseInfo } from '@/types/backup';

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
      useResizeObserver: vi.fn(),
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

  vi.mock('@/store/websocket', () => ({
    useWebsocketStore: () => ({
      connected: ref(false),
      connect: vi.fn(),
      disconnect: vi.fn(),
    }),
  }));

  vi.mock('@/utils/blockie', () => ({
    createBlockie: vi.fn().mockImplementation(({ seed }) => `${seed.toLowerCase()}face`),
  }));

  globalThis.ResizeObserver = vi.fn().mockImplementation(() => ({
    observe: vi.fn(),
    unobserve: vi.fn(),
    disconnect: vi.fn(),
  }));
});

afterEach(() => server.resetHandlers());

afterAll(() => server.close());

function delay(ms: number = 200): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

vi.delay = delay;

// Global stub components
config.global.stubs.RuiIcon = RuiIconStub;
config.global.stubs.RuiTooltip = RuiTooltipStub;
config.global.stubs.RuiAutoComplete = RuiAutoCompleteStub;
config.global.stubs.I18nT = true;

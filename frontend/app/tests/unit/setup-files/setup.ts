import { PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { mockT, mockTc } from '../i18n';

beforeAll(() => {
  Vue.use(Vuetify);
  Vue.use(PiniaVuePlugin);

  vi.mock('@/composables/api/assets/info', () => ({
    useAssetInfoApi: vi.fn().mockReturnValue({
      assetMapping: vi.fn().mockResolvedValue({})
    })
  }));

  vi.mock('@/composables/api/balances/price', () => ({
    usePriceApi: vi.fn().mockReturnValue({
      getPriceCache: vi.fn().mockResolvedValue([]),
      createPriceCache: vi.fn().mockResolvedValue(1),
      deletePriceCache: vi.fn().mockResolvedValue(1),
      queryHistoricalRate: vi.fn().mockResolvedValue(1),
      queryFiatExchangeRates: vi.fn().mockResolvedValue(1),
      queryPrices: vi.fn().mockResolvedValue(1)
    })
  }));

  vi.mock('@/composables/api/session/queried-addresses', () => ({
    useQueriedAddressApi: vi.fn().mockReturnValue({})
  }));

  vi.mock('@/composables/api/backup', () => ({
    useBackupApi: vi.fn().mockReturnValue({
      info: vi.fn().mockReturnValue({})
    })
  }));

  vi.mock('vue', async () => {
    const mod = await vi.importActual<typeof import('vue')>('vue');
    mod.default.config.devtools = false;
    mod.default.config.productionTip = false;
    return {
      ...mod,
      useListeners: vi.fn(),
      useAttrs: vi.fn(),
      useCssModule: vi.fn().mockReturnValue({})
    };
  });

  vi.mock('vue-i18n-composable', async () => {
    const mod = await vi.importActual<typeof import('vue-i18n-composable')>(
      'vue-i18n-composable'
    );

    return {
      ...mod,
      useI18n: () => ({
        t: mockT,
        tc: mockTc
      })
    };
  });

  vi.mock('@/utils/blockie', () => {
    return {
      createBlockie: vi
        .fn()
        .mockImplementation(({ seed }) => `${seed.toLowerCase()}face`)
    };
  });
});

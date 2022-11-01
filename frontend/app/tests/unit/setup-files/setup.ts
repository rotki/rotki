import { PiniaVuePlugin } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { mockT, mockTc } from '../i18n';

beforeAll(() => {
  Vue.use(Vuetify);
  Vue.use(PiniaVuePlugin);

  vi.mock('@/services/assets/info', () => ({
    useAssetInfoApi: vi.fn().mockReturnValue({
      assetMapping: vi.fn().mockResolvedValue({})
    })
  }));

  vi.mock('@/services/balances/price', () => ({
    usePriceApi: vi.fn().mockReturnValue({
      getPriceCache: vi.fn().mockReturnValue([])
    })
  }));

  vi.mock('vue', async () => {
    const mod = await vi.importActual<typeof import('vue')>('vue');
    mod.default.config.devtools = false;
    mod.default.config.productionTip = false;
    return {
      ...mod,
      useListeners: vi.fn(),
      useAttrs: vi.fn()
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
});

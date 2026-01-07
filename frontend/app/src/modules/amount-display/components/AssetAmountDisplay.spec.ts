import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AssetAmountDisplay from '@/modules/amount-display/components/AssetAmountDisplay.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useCurrencies } from '@/types/currencies';
import { CurrencyLocation } from '@/types/currency-location';
import { getDefaultFrontendSettings } from '@/types/settings/frontend-settings';

vi.mock('vue-router', () => ({
  useRoute: vi.fn(),
  useRouter: vi.fn().mockReturnValue({
    push: vi.fn(),
  }),
  createRouter: vi.fn().mockImplementation(() => ({
    beforeEach: vi.fn(),
  })),
  createWebHashHistory: vi.fn(),
}));

const mockAssetInfo = vi.fn().mockImplementation(() => computed(() => ({ symbol: 'ETH' })));

vi.mock('@/composables/assets/retrieval', () => ({
  useAssetInfoRetrieval: (): { assetInfo: typeof mockAssetInfo } => ({
    assetInfo: mockAssetInfo,
  }),
}));

describe('modules/amount-display/components/AssetAmountDisplay', () => {
  let wrapper: VueWrapper<InstanceType<typeof AssetAmountDisplay>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    const { findCurrency } = useCurrencies();

    updateGeneralSettings({
      mainCurrency: findCurrency('EUR'),
      uiFloatingPrecision: 2,
    });

    mockAssetInfo.mockClear();
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('amount display', () => {
    it('should display amount with asset symbol', async () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1.5),
          asset: 'ETH',
        },
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('1.50');
      expect(wrapper.find('[data-cy=display-currency]').text()).toBe('ETH');
    });
  });

  describe('pnl coloring', () => {
    it('should show green for positive values', () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(50),
          asset: 'ETH',
          pnl: true,
        },
      });
      expect(wrapper.find('[data-cy=amount-display].text-rui-success').exists()).toBe(true);
    });

    it('should show red for negative values', () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(-50),
          asset: 'ETH',
          pnl: true,
        },
      });
      expect(wrapper.find('[data-cy=amount-display].text-rui-error').exists()).toBe(true);
    });
  });

  describe('scramble data', () => {
    beforeEach(async () => {
      await useFrontendSettingsStore().updateSetting({ scrambleData: true });
    });

    it('should scramble the amount', async () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1.5),
          asset: 'ETH',
        },
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('1.50');
    });
  });

  describe('currency location', () => {
    it('should show symbol before amount', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        currencyLocation: CurrencyLocation.BEFORE,
      });

      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
        },
      });

      const html = wrapper.html();
      const amountIndex = html.indexOf('display-amount');
      const currencyIndex = html.indexOf('display-currency');
      expect(amountIndex).not.toBe(-1);
      expect(currencyIndex).not.toBe(-1);
      expect(currencyIndex).toBeLessThan(amountIndex);
    });

    it('should show symbol after amount', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        currencyLocation: CurrencyLocation.AFTER,
      });

      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
        },
      });

      const html = wrapper.html();
      const amountIndex = html.indexOf('display-amount');
      const currencyIndex = html.indexOf('display-currency');
      expect(amountIndex).not.toBe(-1);
      expect(currencyIndex).not.toBe(-1);
      expect(currencyIndex).toBeGreaterThan(amountIndex);
    });
  });

  describe('format options', () => {
    it('should display integer when format.integer is true', () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(128.205),
          asset: 'ETH',
          format: { integer: true },
        },
      });
      // Asset amounts use amountRoundingMode which defaults to ROUND_UP
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('129');
    });
  });

  describe('noCollectionParent', () => {
    it('should pass collectionParent: true by default', () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
        },
      });

      expect(mockAssetInfo).toHaveBeenCalled();
      const optionsArg = mockAssetInfo.mock.calls[0][1];
      expect(get(optionsArg)).toEqual({ collectionParent: true });
    });

    it('should pass collectionParent: false when noCollectionParent is true', () => {
      wrapper = mount(AssetAmountDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
          noCollectionParent: true,
        },
      });

      expect(mockAssetInfo).toHaveBeenCalled();
      const optionsArg = mockAssetInfo.mock.calls[0][1];
      expect(get(optionsArg)).toEqual({ collectionParent: false });
    });
  });
});

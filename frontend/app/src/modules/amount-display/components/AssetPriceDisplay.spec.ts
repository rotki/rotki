import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AssetPriceDisplay from '@/modules/amount-display/components/AssetPriceDisplay.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useCurrencies } from '@/types/currencies';

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

describe('modules/amount-display/components/AssetPriceDisplay', () => {
  let wrapper: VueWrapper<InstanceType<typeof AssetPriceDisplay>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    const { findCurrency } = useCurrencies();

    updateGeneralSettings({
      mainCurrency: findCurrency('EUR'),
      uiFloatingPrecision: 2,
    });

    const { prices } = storeToRefs(useBalancePricesStore());
    set(prices, {
      ETH: {
        isManualPrice: false,
        oracle: 'coingecko',
        value: bigNumberify(2000),
      },
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('price display', () => {
    it('should display asset price', async () => {
      wrapper = mount(AssetPriceDisplay, {
        global: { plugins: [pinia] },
        props: { asset: 'ETH' },
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('2,000.00');
    });

    it('should display zero for unknown asset', async () => {
      wrapper = mount(AssetPriceDisplay, {
        global: { plugins: [pinia] },
        props: { asset: 'UNKNOWN_ASSET' },
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('0.00');
    });
  });

  describe('no scrambling', () => {
    beforeEach(async () => {
      await useFrontendSettingsStore().updateSetting({ scrambleData: true });
    });

    it('should NOT scramble price (prices are public data)', async () => {
      wrapper = mount(AssetPriceDisplay, {
        global: { plugins: [pinia] },
        props: { asset: 'ETH' },
      });
      // Price should still be visible even with scrambleData enabled
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('2,000.00');
    });
  });

  describe('oracle info', () => {
    it('should show oracle information on hover', async () => {
      wrapper = mount(AssetPriceDisplay, {
        global: { plugins: [pinia] },
        props: { asset: 'ETH' },
      });

      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();

      expect(wrapper.find('span[class*=chip] > div:last-child').text()).toBe('lu-info coingecko');
    });

    it('should show manual price indicator', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          isManualPrice: true,
          oracle: 'manualcurrent',
          value: bigNumberify(2000),
        },
      });

      wrapper = mount(AssetPriceDisplay, {
        global: { plugins: [pinia] },
        props: { asset: 'ETH' },
      });

      expect(wrapper.find('.rui-icon').exists()).toBe(true);
    });
  });

  describe('format options', () => {
    it('should display integer when format.integer is true', () => {
      wrapper = mount(AssetPriceDisplay, {
        global: { plugins: [pinia] },
        props: {
          asset: 'ETH',
          format: { integer: true },
        },
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('2,000');
    });
  });
});

import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AssetValueDisplay from '@/modules/amount-display/components/AssetValueDisplay.vue';
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

describe('modules/amount-display/components/AssetValueDisplay', () => {
  let wrapper: VueWrapper<InstanceType<typeof AssetValueDisplay>>;
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

  describe('value calculation', () => {
    it('should display asset value (amount * price)', async () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(2),
          asset: 'ETH',
        },
      });
      // 2 ETH * 2000 EUR = 4000 EUR
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('4,000.00');
    });

    it('should display zero for zero amount', async () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(0),
          asset: 'ETH',
        },
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('0.00');
    });
  });

  describe('pnl coloring', () => {
    it('should show green for positive values', () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
          pnl: true,
        },
      });
      expect(wrapper.find('[data-cy=amount-display].text-rui-success').exists()).toBe(true);
    });

    it('should show red for negative values', () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(-1),
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

    it('should scramble the value', async () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(2),
          asset: 'ETH',
        },
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('4,000.00');
    });
  });

  describe('oracle info', () => {
    it('should show oracle information on hover', async () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
        },
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

      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
        },
      });

      expect(wrapper.find('.rui-icon').exists()).toBe(true);
    });
  });

  describe('format options', () => {
    it('should display integer when format.integer is true', () => {
      wrapper = mount(AssetValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          amount: bigNumberify(1),
          asset: 'ETH',
          format: { integer: true },
        },
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('2,000');
    });
  });
});

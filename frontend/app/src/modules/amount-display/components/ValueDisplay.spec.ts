import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ValueDisplay from '@/modules/amount-display/components/ValueDisplay.vue';
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

describe('modules/amount-display/components/ValueDisplay', () => {
  let wrapper: VueWrapper<InstanceType<typeof ValueDisplay>>;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    const { findCurrency } = useCurrencies();

    updateGeneralSettings({
      mainCurrency: findCurrency('EUR'),
      uiFloatingPrecision: 2,
    });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('value display', () => {
    it('should display raw numeric value', async () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: { value: bigNumberify(1.5) },
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('1.50');
    });

    it('should display value with custom symbol', async () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          symbol: 'ETH',
          value: bigNumberify(1.5),
        },
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('1.50');
      expect(wrapper.find('[data-cy=display-currency]').text()).toBe('ETH');
    });

    it('should display value without symbol when symbol is empty', async () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          symbol: '',
          value: bigNumberify(1.5),
        },
      });
      expect(wrapper.find('[data-cy=display-currency]').exists()).toBe(false);
    });
  });

  describe('pnl coloring', () => {
    it('should show green for positive values', () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          pnl: true,
          value: bigNumberify(50),
        },
      });
      expect(wrapper.find('[data-cy=amount-display].text-rui-success').exists()).toBe(true);
    });

    it('should show red for negative values', () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          pnl: true,
          value: bigNumberify(-50),
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
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: { value: bigNumberify(1.5) },
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('1.50');
    });
  });

  describe('format options', () => {
    it('should display integer when format.integer is true', () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          format: { integer: true },
          value: bigNumberify(128.205),
        },
      });
      // Uses amountRoundingMode which defaults to ROUND_UP
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('129');
    });
  });

  describe('loading state', () => {
    it('should show loading skeleton', () => {
      wrapper = mount(ValueDisplay, {
        global: { plugins: [pinia] },
        props: {
          loading: true,
          value: bigNumberify(1.5),
        },
      });
      expect(wrapper.find('[data-cy="amount-display"].skeleton').exists()).toBe(true);
      // Content should be hidden when loading
      expect(wrapper.find('[data-cy="display-amount"]').exists()).toBe(false);
    });
  });
});

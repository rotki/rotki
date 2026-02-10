import type { Pinia } from 'pinia';
import { bigNumberify } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { type ComponentMountingOptions, mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import FiatDisplay from '@/modules/amount-display/components/FiatDisplay.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useCurrencies } from '@/types/currencies';

describe('modules/amount-display/components/FiatDisplay', () => {
  let wrapper: VueWrapper<InstanceType<typeof FiatDisplay>>;
  let pinia: Pinia;

  function createWrapper(props: ComponentMountingOptions<typeof FiatDisplay>['props']): VueWrapper<InstanceType<typeof FiatDisplay>> {
    return mount(FiatDisplay, {
      global: { plugins: [pinia] },
      props,
    });
  }

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    const { findCurrency } = useCurrencies();

    updateGeneralSettings({
      mainCurrency: findCurrency('EUR'),
      uiFloatingPrecision: 2,
    });

    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(exchangeRates, { EUR: bigNumberify(1.2) });
  });

  afterEach(() => {
    wrapper.unmount();
  });

  describe('no conversion', () => {
    it('should display value as-is when from is not provided', async () => {
      wrapper = createWrapper({ value: bigNumberify(1.20440001) });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('1.20');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.20440001');
    });
  });

  describe('fiat conversion', () => {
    it('should convert USD to EUR', async () => {
      wrapper = createWrapper({
        from: 'USD',
        value: bigNumberify(1.20440001),
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('1.44');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.445280012');
    });

    it('should not convert when from equals user currency', async () => {
      wrapper = createWrapper({
        from: 'EUR',
        value: bigNumberify(1.20440001),
      });
      expect(wrapper.find('[data-cy=amount-display]').text()).toMatch('1.20');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.20440001');
    });
  });

  describe('pnl coloring', () => {
    it('should show green for positive values', () => {
      wrapper = createWrapper({
        pnl: true,
        value: bigNumberify(50),
      });
      expect(wrapper.find('[data-cy=amount-display].text-rui-success').exists()).toBe(true);
    });

    it('should show red for negative values', () => {
      wrapper = createWrapper({
        pnl: true,
        value: bigNumberify(-50),
      });
      expect(wrapper.find('[data-cy=amount-display].text-rui-error').exists()).toBe(true);
    });
  });

  describe('scramble data', () => {
    beforeEach(async () => {
      await useFrontendSettingsStore().updateSetting({ scrambleData: true });
    });

    it('should scramble the value', async () => {
      wrapper = createWrapper({
        from: 'USD',
        value: bigNumberify(1.20440001),
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('1.44');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe('1.445280012');
    });

    it('should not scramble the value when noScramble is true', async () => {
      wrapper = createWrapper({
        from: 'USD',
        noScramble: true,
        value: bigNumberify(1.20440001),
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toMatch('1.44');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toMatch('1.445280012');
    });

    it('should not scramble the value when priceAsset is set', async () => {
      wrapper = createWrapper({
        from: 'USD',
        priceAsset: 'ETH',
        value: bigNumberify(1.20440001),
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toMatch('1.44');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toMatch('1.445280012');
    });
  });

  describe('historic prices', () => {
    it('should use historic rate when timestamp is provided', async () => {
      const getPrice = vi.spyOn(useHistoricCachePriceStore(), 'historicPriceInCurrentCurrency');
      getPrice.mockReturnValue(computed(() => bigNumberify(1.2)));
      vi.spyOn(useHistoricCachePriceStore(), 'isPending').mockReturnValue(computed(() => false));

      wrapper = createWrapper({
        from: 'USD',
        timestamp: 1000,
        value: bigNumberify(1),
      });

      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      expect(getPrice).toHaveBeenCalledWith('USD', 1000);
    });

    it('should use historic rate when timestamp with ms is provided', async () => {
      const getPrice = vi.spyOn(useHistoricCachePriceStore(), 'historicPriceInCurrentCurrency');
      getPrice.mockReturnValue(computed(() => bigNumberify(1.2)));
      vi.spyOn(useHistoricCachePriceStore(), 'isPending').mockReturnValue(computed(() => false));

      wrapper = createWrapper({
        from: 'USD',
        timestamp: { ms: 1000000 },
        value: bigNumberify(1),
      });

      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      expect(getPrice).toHaveBeenCalledWith('USD', 1000);
    });
  });

  describe('format options', () => {
    it('should display integer when format.integer is true', () => {
      wrapper = createWrapper({
        format: { integer: true },
        value: bigNumberify(128.205),
      });
      // Default rounding mode rounds down
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('128');
    });
  });
});

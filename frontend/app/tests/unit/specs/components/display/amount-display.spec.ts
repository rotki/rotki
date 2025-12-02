import type { Pinia } from 'pinia';
import { BigNumber, bigNumberify, Zero } from '@rotki/common';
import { createCustomPinia } from '@test/utils/create-pinia';
import { updateGeneralSettings } from '@test/utils/general-settings';
import { mount, type VueWrapper } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import AmountDisplay, { type AmountInputProps } from '@/components/display/amount/AmountDisplay.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
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

describe('amountDisplay.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof AmountDisplay>>;
  let pinia: Pinia;

  const createWrapper = (
    value: BigNumber,
    props: Omit<AmountInputProps, 'value'> = {},
  ) =>
    mount(AmountDisplay, {
      global: {
        plugins: [pinia],
      },
      props: {
        value,
        ...props,
      },
    });

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

  describe('common case', () => {
    it('displays amount converted to selected fiat currency', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD',
      });
      expect(wrapper.find('[data-cy=amount-display]:nth-child(1)').text()).toMatch('1.44');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.445280012');
    });

    it('displays amount converted to selected fiat currency (does not double-convert)', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        amount: bigNumberify(1.20440001),
        fiatCurrency: 'EUR',
      });
      expect(wrapper.find('[data-cy=amount-display]:nth-child(1)').text()).toMatch('1.20');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.20440001');
    });

    it('displays amount as it is without fiat conversion', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001));
      expect(
        wrapper
          .find('[data-cy=amount-display]:nth-child(1)')
          .text()
          .replace(/ +(?= )/g, ''),
      ).toBe('<1.21');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.20540001');
    });

    it('display amount do not show decimal when `integer=true`', () => {
      wrapper = createWrapper(bigNumberify(128.205), { integer: true });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('129');
    });

    it('displays amount do not converted to selected fiat currency when `forceCurrency=true`', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD',
        forceCurrency: true,
      });
      expect(wrapper.find('[data-cy=amount-display]:nth-child(1)').text()).toMatch('1.20');
      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy=display-full-value]').text()).toMatch('1.20440001');
    });
  });

  describe('check PnL', () => {
    it('check if profit', () => {
      const wrapper = createWrapper(bigNumberify(50), { pnl: true });
      expect(wrapper.find('[data-cy=amount-display].text-rui-success').exists()).toBe(true);
    });

    it('check if loss', () => {
      const wrapper = createWrapper(bigNumberify(-50), { pnl: true });
      expect(wrapper.find('[data-cy=amount-display].text-rui-error').exists()).toBe(true);
    });
  });

  describe('scramble data', () => {
    beforeEach(async () => {
      await useFrontendSettingsStore().updateSetting({ scrambleData: true });
    });

    it('displays amount converted to selected fiat currency as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD',
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('1.44');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe('1.445280012');
    });

    it('displays amount converted to selected fiat currency (does not double-convert) as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        amount: bigNumberify(1.20440001),
        fiatCurrency: 'EUR',
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('1.20');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe('1.20440001');
    });

    it('displays amount as it is without fiat conversion as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe('1.21');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe('1.20540001');
    });
  });

  describe('check currency location', () => {
    describe('before', () => {
      beforeEach(() => {
        useFrontendSettingsStore().update({
          ...getDefaultFrontendSettings(),
          currencyLocation: CurrencyLocation.BEFORE,
        });
      });

      it('fiat symbol before amount', () => {
        wrapper = createWrapper(bigNumberify(1), { showCurrency: 'symbol' });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeLessThan(amountIndex);
      });

      it('asset symbol before amount', () => {
        wrapper = createWrapper(bigNumberify(1), {
          asset: 'ETH',
          showCurrency: 'symbol',
        });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeLessThan(amountIndex);
      });
    });

    describe('after', () => {
      beforeEach(() => {
        useFrontendSettingsStore().update({
          ...getDefaultFrontendSettings(),
          currencyLocation: CurrencyLocation.AFTER,
        });
      });

      it('fiat symbol after amount', () => {
        wrapper = createWrapper(bigNumberify(1), { showCurrency: 'symbol' });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeGreaterThan(amountIndex);
      });

      it('asset symbol after amount', () => {
        wrapper = createWrapper(bigNumberify(1), {
          asset: 'ETH',
          showCurrency: 'symbol',
        });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeGreaterThan(amountIndex);
      });
    });
  });

  describe('check separator', () => {
    it('`Thousand separator=,` & `Decimal separator=.`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        thousandSeparator: ',',
        decimalSeparator: '.',
      });

      const wrapper = createWrapper(bigNumberify(123456.78));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('123,456.78');
    });

    it('`Thousand separator=.` & `Decimal separator=,`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        thousandSeparator: '.',
        decimalSeparator: ',',
      });

      const wrapper = createWrapper(bigNumberify(123456.78));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('123.456,78');
    });
  });

  describe('check rounding', () => {
    it('`amountRoundingMode=up`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        amountRoundingMode: BigNumber.ROUND_UP,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
    });

    it('`amountRoundingMode=down`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        amountRoundingMode: BigNumber.ROUND_DOWN,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
    });

    it('`valueRoundingMode=up`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        valueRoundingMode: BigNumber.ROUND_UP,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001), {
        fiatCurrency: 'EUR',
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
    });

    it('`valueRoundingMode=down`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        valueRoundingMode: BigNumber.ROUND_DOWN,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001), {
        fiatCurrency: 'EUR',
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
    });
  });

  describe('check large number abbreviations', () => {
    it('`abbreviateNumber=true`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        abbreviateNumber: true,
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.24 M');
    });

    it('`abbreviateNumber=true`, `minimumDigitToBeAbbreviated=7`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        abbreviateNumber: true,
        minimumDigitToBeAbbreviated: 7,
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.24 M');
    });

    it('`abbreviateNumber=true`, `minimumDigitToBeAbbreviated=8`', () => {
      useFrontendSettingsStore().update({
        ...getDefaultFrontendSettings(),
        abbreviateNumber: true,
        minimumDigitToBeAbbreviated: 8,
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1,234,567.89');
    });
  });

  describe('check manual latest prices', () => {
    it('show oracle information', async () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          oracle: 'coingecko',
          value: bigNumberify(500),
          isManualPrice: false,
        },
      });

      const wrapper = createWrapper(bigNumberify(500), {
        priceAsset: 'ETH',
        isAssetPrice: true,
      });

      await wrapper.find('[data-cy=display-amount]').trigger('mouseover');
      await nextTick();

      expect(wrapper.find('span[class*=chip] > div:last-child').text()).toBe('lu-info coingecko');
    });

    it('shows manual price indicator', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          oracle: 'manualcurrent',
          value: bigNumberify(500),
          isManualPrice: true,
        },
      });

      const wrapper = createWrapper(bigNumberify(500), {
        priceAsset: 'ETH',
      });

      expect(wrapper.find('.rui-icon').exists()).toBe(true);
    });
  });

  it('check current currency manual latest prices', () => {
    const { prices } = storeToRefs(useBalancePricesStore());
    set(prices, {
      ETH: {
        oracle: 'manualcurrent',
        value: bigNumberify(500),
        isManualPrice: true,
      },
    });

    const priceWrapper = createWrapper(bigNumberify(400), {
      priceAsset: 'ETH',
      priceOfAsset: bigNumberify(500),
      fiatCurrency: 'USD',
    });

    const valueWrapper = createWrapper(bigNumberify(800), {
      amount: bigNumberify(2),
      priceAsset: 'ETH',
      priceOfAsset: bigNumberify(500),
      fiatCurrency: 'USD',
    });

    expect(priceWrapper.find('[data-cy="display-amount"]').text()).toBe('480.00');
    expect(valueWrapper.find('[data-cy="display-amount"]').text()).toBe('960.00');
  });

  describe('uses historic price', () => {
    it('when timestamp is set and prices exists', async () => {
      const getPrice = vi.spyOn(useHistoricCachePriceStore(), 'historicPriceInCurrentCurrency');
      getPrice.mockReturnValue(computed(() => bigNumberify(1.2)));

      vi.spyOn(useHistoricCachePriceStore(), 'isPending').mockReturnValue(computed(() => false));

      wrapper = createWrapper(bigNumberify(1), {
        fiatCurrency: 'USD',
        timestamp: 1000,
      });

      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      expect(getPrice).toHaveBeenCalledWith('USD', 1000);
    });

    it('when timestamp is set and prices does not exist', async () => {
      const getPrice = vi.spyOn(useHistoricCachePriceStore(), 'historicPriceInCurrentCurrency');
      getPrice.mockReturnValue(computed(() => Zero));

      vi.spyOn(useHistoricCachePriceStore(), 'isPending').mockReturnValue(computed(() => false));

      wrapper = createWrapper(bigNumberify(1), {
        fiatCurrency: 'USD',
        timestamp: 1000,
      });

      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('0.00');
      expect(getPrice).toHaveBeenCalledWith('USD', 1000);
    });
  });
  describe('subscript display', () => {
    beforeEach(async () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({
        ...getDefaultFrontendSettings(),
        subscriptDecimals: true,
      });

      updateGeneralSettings({
        uiFloatingPrecision: 10,
      });

      await nextTick();
      await flushPromises();
    });

    describe('small decimal numbers', () => {
      it('shows correct subscript count for numbers with multiple leading zeros', async () => {
        wrapper = createWrapper(bigNumberify('0.0000000815'));
        await nextTick();
        await flushPromises();

        const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
        expect(subscriptElement.exists()).toBe(true);
        expect(subscriptElement.text()).toBe('7');
      });

      it('shows correct subscript count for very small numbers', async () => {
        wrapper = createWrapper(bigNumberify('0.000000000123'));
        await nextTick();
        await flushPromises();

        const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
        expect(subscriptElement.exists()).toBe(true);
        expect(subscriptElement.text()).toBe('9');
      });

      it('shows no subscript for number with only one leading zero', async () => {
        wrapper = createWrapper(bigNumberify('0.0123'));
        await nextTick();
        await flushPromises();

        const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
        expect(subscriptElement.exists()).toBe(false);
      });
    });

    describe('non-subscript cases', () => {
      it('shows no subscript for numbers greater than or equal to 1', async () => {
        wrapper = createWrapper(bigNumberify('1.000000000123'));
        await nextTick();
        await flushPromises();

        const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
        expect(subscriptElement.exists()).toBe(false);
      });

      it('handles regular numbers without subscript', async () => {
        wrapper = createWrapper(bigNumberify('1.23'));
        await nextTick();
        await flushPromises();

        const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
        expect(subscriptElement.exists()).toBe(false);
      });
    });

    it('respects disabled subscript setting', async () => {
      const frontendStore = useFrontendSettingsStore();
      frontendStore.update({
        ...getDefaultFrontendSettings(),
        subscriptDecimals: false,
      });

      wrapper = createWrapper(bigNumberify('0.0000000815'));
      await nextTick();
      await flushPromises();

      const subscriptElement = wrapper.find('[data-cy="amount-display-subscript"]');
      expect(subscriptElement.exists()).toBe(false);
    });
  });
});

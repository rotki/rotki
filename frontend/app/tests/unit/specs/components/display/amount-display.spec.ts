import { BigNumber } from '@rotki/common';
import { type VueWrapper, mount } from '@vue/test-utils';
import flushPromises from 'flush-promises';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { type ShownCurrency, useCurrencies } from '@/types/currencies';
import { CurrencyLocation } from '@/types/currency-location';
import { FrontendSettings } from '@/types/settings/frontend-settings';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { createCustomPinia } from '../../../utils/create-pinia';
import { updateGeneralSettings } from '../../../utils/general-settings';
import type { Pinia } from 'pinia';

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

describe('components/display/AmountDisplay.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof AmountDisplay>>;
  let pinia: Pinia;

  const createWrapper = (
    value: BigNumber,
    props: {
      fiatCurrency?: string;
      amount?: BigNumber;
      integer?: boolean;
      forceCurrency?: boolean;
      pnl?: boolean;
      showCurrency?: ShownCurrency;
      asset?: string;
      priceAsset?: string;
      priceOfAsset?: BigNumber;
      timestamp?: number;
    } = {},
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
    useSessionStore().$reset();
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
    beforeEach(() => {
      useSessionSettingsStore().update({ scrambleData: true });
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
          ...FrontendSettings.parse({}),
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
          ...FrontendSettings.parse({}),
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
        ...FrontendSettings.parse({}),
        thousandSeparator: ',',
        decimalSeparator: '.',
      });

      const wrapper = createWrapper(bigNumberify(123456.78));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('123,456.78');
    });

    it('`Thousand separator=.` & `Decimal separator=,`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
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
        ...FrontendSettings.parse({}),
        amountRoundingMode: BigNumber.ROUND_UP,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
    });

    it('`amountRoundingMode=down`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        amountRoundingMode: BigNumber.ROUND_DOWN,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
    });

    it('`valueRoundingMode=up`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        valueRoundingMode: BigNumber.ROUND_UP,
      });

      const wrapper = createWrapper(bigNumberify(1.20340001), {
        fiatCurrency: 'EUR',
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
    });

    it('`valueRoundingMode=down`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
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
        ...FrontendSettings.parse({}),
        abbreviateNumber: true,
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.24 M');
    });

    it('`abbreviateNumber=true`, `minimumDigitToBeAbbreviated=7`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        abbreviateNumber: true,
        minimumDigitToBeAbbreviated: 7,
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.24 M');
    });

    it('`abbreviateNumber=true`, `minimumDigitToBeAbbreviated=8`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        abbreviateNumber: true,
        minimumDigitToBeAbbreviated: 8,
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1,234,567.89');
    });
  });

  describe('check manual latest prices', () => {
    it('does not show manual price indicator', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          value: bigNumberify(500),
          isManualPrice: false,
        },
      });

      const wrapper = createWrapper(bigNumberify(500), {
        priceAsset: 'ETH',
      });

      expect(wrapper.find('.rui-icon').exists()).toBe(false);
    });

    it('shows manual price indicator', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
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

  describe('check current currency manual latest prices', () => {
    it('`isCurrentCurrency=false`', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
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

    it('`isCurrentCurrency=true`', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

      set(prices, {
        ETH: {
          value: bigNumberify(500),
          isManualPrice: true,
        },
      });

      const priceWrapper = createWrapper(bigNumberify(400), {
        priceAsset: 'ETH',
        priceOfAsset: bigNumberify(500),
        fiatCurrency: get(currencySymbol),
      });

      const valueWrapper = createWrapper(bigNumberify(800), {
        amount: bigNumberify(2),
        priceAsset: 'ETH',
        priceOfAsset: bigNumberify(500),
        fiatCurrency: get(currencySymbol),
      });

      expect(priceWrapper.find('[data-cy="display-amount"]').text()).toBe('500.00');
      expect(valueWrapper.find('[data-cy="display-amount"]').text()).toBe('1,000.00');
    });
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
});

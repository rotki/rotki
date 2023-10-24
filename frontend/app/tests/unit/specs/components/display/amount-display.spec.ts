import { BigNumber } from '@rotki/common';
import { type Wrapper, mount } from '@vue/test-utils';
import { type Pinia } from 'pinia';
import Vuetify from 'vuetify';
import flushPromises from 'flush-promises';
import { useCurrencies } from '@/types/currencies';
import { CurrencyLocation } from '@/types/currency-location';
import { FrontendSettings } from '@/types/settings/frontend-settings';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import createCustomPinia from '../../../utils/create-pinia';
import { updateGeneralSettings } from '../../../utils/general-settings';

vi.mocked(useCssModule).mockReturnValue({
  blur: 'blur',
  profit: 'profit',
  loss: 'loss',
  display: 'display'
});

describe('AmountDisplay.vue', () => {
  let wrapper: Wrapper<any>;
  let pinia: Pinia;

  const createWrapper = (
    value: BigNumber,
    props: {
      fiatCurrency?: string;
      amount?: BigNumber;
      integer?: boolean;
      forceCurrency?: boolean;
      pnl?: boolean;
      showCurrency?: string;
      asset?: string;
      priceAsset?: string;
      priceOfAsset?: BigNumber;
      timestamp?: number;
    } = {}
  ) => {
    const vuetify = new Vuetify();
    return mount(AmountDisplay, {
      pinia,
      vuetify,
      propsData: {
        value,
        ...props
      }
    });
  };

  beforeEach(async () => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
    document.body.dataset.app = 'true';
    const { findCurrency } = useCurrencies();

    updateGeneralSettings({
      mainCurrency: findCurrency('EUR'),
      uiFloatingPrecision: 2
    });

    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(exchangeRates, { EUR: bigNumberify(1.2) });
  });

  afterEach(() => {
    useSessionStore().$reset();
  });

  describe('Common case', () => {
    test('displays amount converted to selected fiat currency', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.44');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.445280012'
      );
    });

    test('displays amount converted to selected fiat currency (does not double-convert)', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        amount: bigNumberify(1.20440001),
        fiatCurrency: 'EUR'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.20440001'
      );
    });

    test('displays amount as it is without fiat conversion', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001));
      expect(wrapper.find('[data-cy="display-comparison-symbol"]').text()).toBe(
        '<'
      );
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.20540001'
      );
    });

    test('display amount do not show decimal when `integer=true`', () => {
      wrapper = createWrapper(bigNumberify(128.205), { integer: true });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('129');
    });

    test('displays amount do not converted to selected fiat currency when `forceCurrency=true`', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD',
        forceCurrency: true
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.20440001'
      );
    });
  });

  describe('Check PnL', () => {
    test('Check if profit', () => {
      const wrapper = createWrapper(bigNumberify(50), { pnl: true });
      expect(wrapper.find('[data-cy="display-wrapper"].profit').exists()).toBe(
        true
      );
    });

    test('Check if loss', () => {
      const wrapper = createWrapper(bigNumberify(-50), { pnl: true });
      expect(wrapper.find('[data-cy="display-wrapper"].loss').exists()).toBe(
        true
      );
    });
  });

  describe('Scramble data', () => {
    beforeEach(() => {
      useSessionSettingsStore().update({ scrambleData: true });
    });

    test('displays amount converted to selected fiat currency as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe(
        '1.44'
      );
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe(
        '1.445280012'
      );
    });

    test('displays amount converted to selected fiat currency (does not double-convert) as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        amount: bigNumberify(1.20440001),
        fiatCurrency: 'EUR'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe(
        '1.20'
      );
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe(
        '1.20440001'
      );
    });

    test('displays amount as it is without fiat conversion as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe(
        '1.21'
      );
      await wrapper.find('[data-cy="display-amount"]').trigger('mouseover');
      await wrapper.vm.$nextTick();
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe(
        '1.20540001'
      );
    });
  });

  describe('Check currency location', () => {
    describe('Before', () => {
      beforeEach(() => {
        useFrontendSettingsStore().update({
          ...FrontendSettings.parse({}),
          currencyLocation: CurrencyLocation.BEFORE
        });
      });

      test('fiat symbol before amount', () => {
        wrapper = createWrapper(bigNumberify(1), { showCurrency: 'symbol' });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeLessThan(amountIndex);
      });

      test('asset symbol before amount', () => {
        wrapper = createWrapper(bigNumberify(1), {
          asset: 'ETH',
          showCurrency: 'symbol'
        });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeLessThan(amountIndex);
      });
    });

    describe('After', () => {
      beforeEach(() => {
        useFrontendSettingsStore().update({
          ...FrontendSettings.parse({}),
          currencyLocation: CurrencyLocation.AFTER
        });
      });

      test('fiat symbol after amount', () => {
        wrapper = createWrapper(bigNumberify(1), { showCurrency: 'symbol' });
        const html = wrapper.html();
        const amountIndex = html.indexOf('display-amount');
        const currencyIndex = html.indexOf('display-currency');
        expect(amountIndex).not.toBe(-1);
        expect(currencyIndex).not.toBe(-1);
        expect(currencyIndex).toBeGreaterThan(amountIndex);
      });

      test('asset symbol after amount', () => {
        wrapper = createWrapper(bigNumberify(1), {
          asset: 'ETH',
          showCurrency: 'symbol'
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

  describe('Check separator', () => {
    test('`Thousand separator=,` & `Decimal separator=.`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        thousandSeparator: ',',
        decimalSeparator: '.'
      });

      const wrapper = createWrapper(bigNumberify(123456.78));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe(
        '123,456.78'
      );
    });

    test('`Thousand separator=.` & `Decimal separator=,`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        thousandSeparator: '.',
        decimalSeparator: ','
      });

      const wrapper = createWrapper(bigNumberify(123456.78));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe(
        '123.456,78'
      );
    });
  });

  describe('Check rounding', () => {
    test('`amountRoundingMode=up`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        amountRoundingMode: BigNumber.ROUND_UP
      });

      const wrapper = createWrapper(bigNumberify(1.20340001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
    });

    test('`amountRoundingMode=down`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        amountRoundingMode: BigNumber.ROUND_DOWN
      });

      const wrapper = createWrapper(bigNumberify(1.20340001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
    });

    test('`valueRoundingMode=up`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        valueRoundingMode: BigNumber.ROUND_UP
      });

      const wrapper = createWrapper(bigNumberify(1.20340001), {
        fiatCurrency: 'EUR'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
    });

    test('`valueRoundingMode=down`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        valueRoundingMode: BigNumber.ROUND_DOWN
      });

      const wrapper = createWrapper(bigNumberify(1.20340001), {
        fiatCurrency: 'EUR'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
    });
  });

  describe('Check large number abbreviations', () => {
    test('`abbreviateNumber=true`', () => {
      useFrontendSettingsStore().update({
        ...FrontendSettings.parse({}),
        abbreviateNumber: true
      });

      const wrapper = createWrapper(bigNumberify(1234567.89));
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.24 M');
    });
  });

  describe('Check manual latest prices', () => {
    test('Manual price icon visible', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          value: bigNumberify(500),
          isManualPrice: false,
          isCurrentCurrency: false
        }
      });

      const wrapper = createWrapper(bigNumberify(500), {
        priceAsset: 'ETH'
      });

      expect(wrapper.find('.v-icon.mdi-auto-fix').exists()).toBe(false);
    });

    test('Manual price icon visible', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          value: bigNumberify(500),
          isManualPrice: true,
          isCurrentCurrency: false
        }
      });

      const wrapper = createWrapper(bigNumberify(500), {
        priceAsset: 'ETH'
      });

      expect(wrapper.find('.v-icon.mdi-auto-fix').exists()).toBe(true);
    });
  });

  describe('Check current currency manual latest prices', () => {
    test('`isCurrentCurrency=false`', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          value: bigNumberify(500),
          isManualPrice: true,
          isCurrentCurrency: false
        }
      });

      const priceWrapper = createWrapper(bigNumberify(400), {
        priceAsset: 'ETH',
        priceOfAsset: bigNumberify(500),
        fiatCurrency: 'USD'
      });

      const valueWrapper = createWrapper(bigNumberify(800), {
        amount: bigNumberify(2),
        priceAsset: 'ETH',
        priceOfAsset: bigNumberify(500),
        fiatCurrency: 'USD'
      });

      expect(priceWrapper.find('[data-cy="display-amount"]').text()).toBe(
        '480.00'
      );
      expect(valueWrapper.find('[data-cy="display-amount"]').text()).toBe(
        '960.00'
      );
    });

    test('`isCurrentCurrency=true`', () => {
      const { prices } = storeToRefs(useBalancePricesStore());
      set(prices, {
        ETH: {
          value: bigNumberify(500),
          isManualPrice: true,
          isCurrentCurrency: true
        }
      });

      const priceWrapper = createWrapper(bigNumberify(400), {
        priceAsset: 'ETH',
        priceOfAsset: bigNumberify(500),
        fiatCurrency: 'USD'
      });

      const valueWrapper = createWrapper(bigNumberify(800), {
        amount: bigNumberify(2),
        priceAsset: 'ETH',
        priceOfAsset: bigNumberify(500),
        fiatCurrency: 'USD'
      });

      expect(priceWrapper.find('[data-cy="display-amount"]').text()).toBe(
        '500.00'
      );
      expect(valueWrapper.find('[data-cy="display-amount"]').text()).toBe(
        '1,000.00'
      );
    });
  });

  describe('uses historic price', () => {
    test('when timestamp is set and prices exists', async () => {
      const getPrice = vi.spyOn(
        useHistoricCachePriceStore(),
        'historicPriceInCurrentCurrency'
      );
      getPrice.mockReturnValue(computed(() => bigNumberify(1.2)));

      vi.spyOn(useHistoricCachePriceStore(), 'isPending').mockReturnValue(
        computed(() => false)
      );

      wrapper = createWrapper(bigNumberify(1), {
        fiatCurrency: 'USD',
        timestamp: 1000
      });

      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      expect(getPrice).toHaveBeenCalledWith('USD', 1000);
    });

    test('when timestamp is set and prices does not exist', async () => {
      const getPrice = vi.spyOn(
        useHistoricCachePriceStore(),
        'historicPriceInCurrentCurrency'
      );
      getPrice.mockReturnValue(computed(() => Zero));

      vi.spyOn(useHistoricCachePriceStore(), 'isPending').mockReturnValue(
        computed(() => false)
      );

      wrapper = createWrapper(bigNumberify(1), {
        fiatCurrency: 'USD',
        timestamp: 1000
      });

      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('0.00');
      expect(getPrice).toHaveBeenCalledWith('USD', 1000);
    });
  });
});

import { BigNumber } from '@rotki/common';
import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import { Pinia, setActivePinia, storeToRefs } from 'pinia';
import Vuetify from 'vuetify';
import { VTooltip } from 'vuetify/lib/components';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { defaultGeneralSettings } from '@/data/factories';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useSessionStore } from '@/store/session';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useCurrencies } from '@/types/currencies';
import { CurrencyLocation } from '@/types/currency-location';
import { FrontendSettings } from '@/types/frontend-settings';
import { bigNumberify } from '@/utils/bignumbers';
import '@/filters';
import createCustomPinia from '../../utils/create-pinia';

// This is workaround used because stubs is somehow not working,
// Eager prop will render the <slot /> immediately
// @ts-ignore
VTooltip.options.props.eager.default = true;

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
    document.body.setAttribute('data-app', 'true');
    const store = useGeneralSettingsStore();
    const { findCurrency } = useCurrencies();
    const mainCurrency = findCurrency('EUR');
    store.update({
      ...defaultGeneralSettings(mainCurrency),
      mainCurrency,
      uiFloatingPrecision: 2
    });

    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(exchangeRates, { EUR: bigNumberify(1.2) });
  });

  afterEach(() => {
    useSessionStore().$reset();
  });

  describe('Common case', () => {
    test('displays amount converted to selected fiat currency', () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.44');
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.445280012'
      );
    });

    test('displays amount converted to selected fiat currency (does not double-convert)', () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        amount: bigNumberify(1.20440001),
        fiatCurrency: 'EUR'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.20440001'
      );
    });

    test('displays amount as it is without fiat conversion', () => {
      wrapper = createWrapper(bigNumberify(1.20540001));
      expect(wrapper.find('[data-cy="display-comparison-symbol"]').text()).toBe(
        '<'
      );
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.21');
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.20540001'
      );
    });

    test('display amount do not show decimal when `integer=true`', () => {
      wrapper = createWrapper(bigNumberify(128.205), { integer: true });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('129');
    });

    test('displays amount do not converted to selected fiat currency when `forceCurrency=true`', () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD',
        forceCurrency: true
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).toBe('1.20');
      expect(wrapper.find('[data-cy="display-full-value"]').text()).toBe(
        '1.20440001'
      );
    });
  });

  describe('Check PnL', () => {
    test('Check if profit', () => {
      const wrapper = createWrapper(bigNumberify(50), { pnl: true });
      expect(wrapper.find('.amount-display--profit').exists()).toBe(true);
    });

    test('Check if loss', () => {
      const wrapper = createWrapper(bigNumberify(-50), { pnl: true });
      expect(wrapper.find('.amount-display--loss').exists()).toBe(true);
    });
  });

  describe('Scramble data', () => {
    beforeEach(() => {
      useSessionSettingsStore().update({ scrambleData: true });
    });

    test('displays amount converted to selected fiat currency as scrambled', () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        fiatCurrency: 'USD'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe(
        '1.44'
      );
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe(
        '1.445280012'
      );
    });

    test('displays amount converted to selected fiat currency (does not double-convert) as scrambled', () => {
      wrapper = createWrapper(bigNumberify(1.20440001), {
        amount: bigNumberify(1.20440001),
        fiatCurrency: 'EUR'
      });
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe(
        '1.20'
      );
      expect(wrapper.find('[data-cy="display-full-value"]').text()).not.toBe(
        '1.20440001'
      );
    });

    test('displays amount as it is without fiat conversion as scrambled', () => {
      wrapper = createWrapper(bigNumberify(1.20540001));
      expect(wrapper.find('[data-cy="display-amount"]').text()).not.toBe(
        '1.21'
      );
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
});

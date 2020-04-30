import { mount, Wrapper } from '@vue/test-utils';
import { default as BigNumber } from 'bignumber.js';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { currencies } from '@/data/currencies';
import store from '@/store/store';
import { Zero, bigNumberify } from '@/utils/bignumbers';
import '@/filters';

Vue.use(Vuetify);

function createWrapper(value: BigNumber, amount: BigNumber, fiatCurrency: string | null) {
  let vuetify: typeof Vuetify = new Vuetify();
  return mount(AmountDisplay, {
    store,
    vuetify,
    stubs: ['v-tooltip'],
    propsData: {
      value,
      fiatCurrency,
      amount
    }
  });
}

describe('AmountDisplay.vue', () => {
  let wrapper: Wrapper<AmountDisplay>;

  describe('Common case', () => {
    beforeEach(() => {
      store.commit('session/defaultCurrency', currencies[1]);
      store.commit('balances/usdToFiatExchangeRates', { EUR: 1.2 });
      store.commit('session/settings', { floatingPrecision: 2 });
    });

    afterEach(() => {
      store.commit('session/reset');
    });

    test('displays amount converted to selected fiat currency', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), Zero, 'USD');
      expect(wrapper.find('.amount-display__value').text()).toMatch('1.45');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount converted to selected fiat currency (does not double-convert)', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), bigNumberify(1.20440001), 'EUR');
      expect(wrapper.find('.amount-display__value').text()).toMatch('1.20');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount as it is without fiat conversion', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001), Zero, null);
      expect(wrapper.find('.amount-display__value').text()).toMatch('1.21');
      expect(wrapper.find('.amount-display__full-value').text()).toMatch(
        '1.20540001'
      );
    });
  });

  describe('Scramble data', () => {
    beforeEach(() => {
      store.commit('session/defaultCurrency', currencies[1]);
      store.commit('balances/usdToFiatExchangeRates', { EUR: 1.2 });
      store.commit('session/settings', { floatingPrecision: 2 });
      store.commit('session/scrambleData', true);
    });

    afterEach(() => {
      store.commit('session/reset');
    });

    test('displays amount converted to selected fiat currency as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), Zero, 'USD');
      expect(wrapper.find('.amount-display__value').text()).not.toMatch('1.45');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount converted to selected fiat currency (does not double-convert) as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), bigNumberify(1.20440001), 'EUR');
      expect(wrapper.find('.amount-display__value').text()).not.toMatch('1.20');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount as it is without fiat conversion as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001), Zero, null);
      expect(wrapper.find('.amount-display__value').text()).not.toMatch('1.21');
      expect(wrapper.find('.amount-display__full-value').text()).not.toMatch(
        '1.20540001'
      );
    });
  });
});

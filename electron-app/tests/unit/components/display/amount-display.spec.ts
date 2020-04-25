import { mount, Wrapper } from '@vue/test-utils';
import { default as BigNumber } from 'bignumber.js';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { currencies } from '@/data/currencies';
import store from '@/store/store';
import { bigNumberify } from '@/utils/bignumbers';
import '@/filters';

Vue.use(Vuetify);

function createWrapper(value: BigNumber, fiat: boolean = false) {
  let vuetify: typeof Vuetify = new Vuetify();
  return mount(AmountDisplay, {
    store,
    vuetify,
    stubs: ['v-tooltip'],
    propsData: {
      value,
      fiat
    }
  });
}

describe('AmountDisplay.vue', () => {
  let wrapper: Wrapper<AmountDisplay>;

  beforeEach(() => {
    store.commit('session/defaultCurrency', currencies[1]);
    store.commit('balances/usdToFiatExchangeRates', { EUR: 1.2 });
    store.commit('session/settings', { floatingPrecision: 2 });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  test('displays amount converted to selected currency on fiat flag', async () => {
    wrapper = createWrapper(bigNumberify(1.20440001), true);
    expect(wrapper.find('.amount-display__value').text()).toMatch('1.45');
    expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
  });

  test('displays amount as it is without the fiat flag', async () => {
    wrapper = createWrapper(bigNumberify(1.20540001));
    expect(wrapper.find('.amount-display__value').text()).toMatch('1.21');
    expect(wrapper.find('.amount-display__full-value').text()).toMatch(
      '1.20540001'
    );
  });
});

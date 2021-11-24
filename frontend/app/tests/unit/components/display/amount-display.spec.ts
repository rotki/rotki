import { BigNumber } from '@rotki/common';
import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { currencies } from '@/data/currencies';
import store from '@/store/store';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import '@/filters';

Vue.use(Vuetify);

function createWrapper(
  value: BigNumber,
  amount: BigNumber,
  fiatCurrency: string | null
) {
  const vuetify = new Vuetify();
  return mount(AmountDisplay, {
    store,
    vuetify,
    stubs: {
      VTooltip: {
        template:
          '<span><slot name="activator"/><slot v-if="!disabled"/></span>',
        props: {
          disabled: { type: Boolean }
        }
      }
    },
    propsData: {
      value,
      fiatCurrency,
      amount
    }
  });
}

describe('AmountDisplay.vue', () => {
  let wrapper: Wrapper<AmountDisplay>;

  beforeEach(async () => {
    store.commit('session/generalSettings', {
      mainCurrency: currencies[1]
    });
    store.commit('balances/usdToFiatExchangeRates', { EUR: 1.2 });
    store.commit('session/generalSettings', { uiFloatingPrecision: 2 });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  describe('Common case', () => {
    test('displays amount converted to selected fiat currency', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), Zero, 'USD');
      expect(wrapper.find('.amount-display__value').text()).toBe('1.44');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount converted to selected fiat currency (does not double-convert)', async () => {
      wrapper = createWrapper(
        bigNumberify(1.20440001),
        bigNumberify(1.20440001),
        'EUR'
      );
      expect(wrapper.find('.amount-display__value').text()).toBe('1.20');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount as it is without fiat conversion', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001), Zero, null);
      expect(wrapper.find('.amount-display__value').text()).toBe('< 1.21');
      expect(wrapper.find('.amount-display__full-value').text()).toBe(
        '1.20540001'
      );
    });
  });

  describe('Scramble data', () => {
    beforeEach(() => {
      store.commit('session/scrambleData', true);
    });

    test('displays amount converted to selected fiat currency as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), Zero, 'USD');
      expect(wrapper.find('.amount-display__value').text()).not.toBe('1.44');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount converted to selected fiat currency (does not double-convert) as scrambled', async () => {
      wrapper = createWrapper(
        bigNumberify(1.20440001),
        bigNumberify(1.20440001),
        'EUR'
      );
      expect(wrapper.find('.amount-display__value').text()).not.toBe('1.20');
      expect(wrapper.find('.amount-display__full-value').exists()).toBe(false);
    });

    test('displays amount as it is without fiat conversion as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20540001), Zero, null);
      expect(wrapper.find('.amount-display__value').text()).not.toBe('1.21');
      expect(wrapper.find('.amount-display__full-value').text()).not.toBe(
        '1.20540001'
      );
    });
  });
});

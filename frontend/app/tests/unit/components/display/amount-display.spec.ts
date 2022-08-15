import { BigNumber } from '@rotki/common';
import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import {
  createPinia,
  Pinia,
  PiniaVuePlugin,
  setActivePinia,
  storeToRefs
} from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import { VTooltip } from 'vuetify/lib/components';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { currencies } from '@/data/currencies';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useSessionStore } from '@/store/session';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { bigNumberify, Zero } from '@/utils/bignumbers';
import '@/filters';
import '../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

// This is workaround used because stubs is somehow not working,
// Eager prop will render the <slot /> immediately
// @ts-ignore
VTooltip.options.props.eager.default = true;

describe('AmountDisplay.vue', () => {
  let wrapper: Wrapper<any>;
  let pinia: Pinia;

  const createWrapper = (
    value: BigNumber,
    amount: BigNumber,
    fiatCurrency: string | null
  ) => {
    const vuetify = new Vuetify();
    return mount(AmountDisplay, {
      pinia,
      vuetify,
      propsData: {
        value,
        fiatCurrency,
        amount
      }
    });
  };

  beforeEach(async () => {
    pinia = createPinia();
    setActivePinia(pinia);
    document.body.setAttribute('data-app', 'true');
    const { uiFloatingPrecision, mainCurrency } = storeToRefs(
      useGeneralSettingsStore()
    );
    const { exchangeRates } = storeToRefs(useBalancePricesStore());
    set(mainCurrency, currencies[1]);
    set(uiFloatingPrecision, 2);
    set(exchangeRates, { EUR: bigNumberify(1.2) });
  });

  afterEach(() => {
    useSessionStore().reset();
  });

  describe('Common case', () => {
    test('displays amount converted to selected fiat currency', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), Zero, 'USD');
      expect(wrapper.find('.amount-display__value').text()).toBe('1.44');
      expect(wrapper.find('.amount-display__full-value').text()).toBe(
        '1.445280012'
      );
    });

    test('displays amount converted to selected fiat currency (does not double-convert)', async () => {
      wrapper = createWrapper(
        bigNumberify(1.20440001),
        bigNumberify(1.20440001),
        'EUR'
      );
      expect(wrapper.find('.amount-display__value').text()).toBe('1.20');
      expect(wrapper.find('.amount-display__full-value').text()).toBe(
        '1.20440001'
      );
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
      const { scrambleData } = storeToRefs(useSessionSettingsStore());
      set(scrambleData, true);
    });

    test('displays amount converted to selected fiat currency as scrambled', async () => {
      wrapper = createWrapper(bigNumberify(1.20440001), Zero, 'USD');
      expect(wrapper.find('.amount-display__value').text()).not.toBe('1.44');
      expect(wrapper.find('.amount-display__full-value').text()).not.toBe(
        '1.445280012'
      );
    });

    test('displays amount converted to selected fiat currency (does not double-convert) as scrambled', async () => {
      wrapper = createWrapper(
        bigNumberify(1.20440001),
        bigNumberify(1.20440001),
        'EUR'
      );
      expect(wrapper.find('.amount-display__value').text()).not.toBe('1.20');
      expect(wrapper.find('.amount-display__full-value').text()).not.toBe(
        '1.20440001'
      );
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

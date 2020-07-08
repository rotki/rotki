import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ManualBalancesList from '@/components/accounts/ManualBalancesList.vue';
import { findCurrency } from '@/data/converters';
import { currencies } from '@/data/currencies';
import store from '@/store/store';

Vue.use(Vuetify);

describe('ManualBalanceList.vue', () => {
  let vuetify: typeof Vuetify;
  let wrapper: Wrapper<ManualBalancesList>;

  beforeEach(() => {
    vuetify = new Vuetify();
    wrapper = mount(ManualBalancesList, {
      stubs: ['v-dialog'],
      store,
      vuetify,
      propsData: {
        value: ''
      }
    });
  });

  test('currency header is properly updated', async () => {
    expect(wrapper.find('th:nth-child(4)').text()).toMatch('USD Value');
    store.commit('session/generalSettings', {
      selectedCurrency: findCurrency(currencies[1].ticker_symbol)
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('th:nth-child(4)').text()).toMatch('EUR Value');
  });
});

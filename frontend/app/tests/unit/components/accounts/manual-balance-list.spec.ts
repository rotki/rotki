import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import ManualBalancesList from '@/components/accounts/ManualBalancesList.vue';
import { findCurrency } from '@/data/converters';
import { currencies } from '@/data/currencies';
import store from '@/store/store';
import '../../i18n';

Vue.use(Vuetify);

describe('ManualBalanceList.vue', () => {
  let wrapper: Wrapper<ManualBalancesList>;

  beforeEach(() => {
    const vuetify = new Vuetify();
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
    expect(wrapper.find('th:nth-child(5)').text()).toContain('USD');
    store.commit('session/generalSettings', {
      selectedCurrency: findCurrency(currencies[1].ticker_symbol)
    });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('th:nth-child(5)').text()).toContain('EUR');
  });
});

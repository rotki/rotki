import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AssetBalances from '@/components/AssetBalances.vue';
import store from '@/store/store';
import '../../i18n';

Vue.use(Vuetify);

describe('AssetBalances.vue', () => {
  let wrapper: Wrapper<any>;
  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(AssetBalances, {
      vuetify,
      store,
      pinia,
      provide: {
        'vuex-store': store
      },
      propsData: {
        balances: []
      }
    });
  });

  afterEach(() => {
    store.commit('session/reset');
  });

  test('table enters into loading state when balances load', async () => {
    await wrapper.setProps({ loading: true });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeTruthy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'asset_balances.loading'
    );

    await wrapper.setProps({ loading: false });
    await wrapper.vm.$nextTick();

    expect(wrapper.find('.v-data-table__progress').exists()).toBeFalsy();
    expect(wrapper.find('.v-data-table__empty-wrapper td').text()).toMatch(
      'No data available'
    );
  });
});

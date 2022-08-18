import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, PiniaVuePlugin, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AssetBalances from '@/components/AssetBalances.vue';
import { useSessionStore } from '@/store/session';
import '../../i18n';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('AssetBalances.vue', () => {
  let wrapper: Wrapper<any>;
  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    wrapper = mount(AssetBalances, {
      vuetify,
      pinia,
      propsData: {
        balances: []
      }
    });
  });

  afterEach(() => {
    useSessionStore().reset();
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

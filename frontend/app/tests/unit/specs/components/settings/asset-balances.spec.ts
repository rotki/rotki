import { type Wrapper, mount } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import AssetBalances from '@/components/AssetBalances.vue';
import createCustomPinia from '../../../utils/create-pinia';

describe('AssetBalances.vue', () => {
  let wrapper: Wrapper<any>;
  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createCustomPinia();
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
    useSessionStore().$reset();
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

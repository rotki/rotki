import { mount, Wrapper } from '@vue/test-utils';
import AssetBalances from '@/components/AssetBalances.vue';
import store from '@/store/store';
import { mountOptions } from '../../utils/mount';

describe('AssetBalances.vue', () => {
  let wrapper: Wrapper<any>;
  beforeEach(() => {
    const options = mountOptions();
    wrapper = mount(AssetBalances, {
      ...options,
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

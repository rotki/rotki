import { type Wrapper, mount } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import AssetBalances from '@/components/AssetBalances.vue';
import { createCustomPinia } from '../../../utils/create-pinia';
import { libraryDefaults } from '../../../utils/provide-defaults';

describe('assetBalances.vue', () => {
  let wrapper: Wrapper<any>;
  beforeEach(() => {
    const vuetify = new Vuetify();
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    wrapper = mount(AssetBalances, {
      vuetify,
      pinia,
      propsData: {
        balances: [],
      },
      provide: libraryDefaults,
    });
  });

  afterEach(() => {
    useSessionStore().$reset();
  });

  it('table enters into loading state when balances load', async () => {
    await wrapper.setProps({ loading: true });
    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBeTruthy();

    await wrapper.setProps({ loading: false });
    await nextTick();

    expect(wrapper.find('tbody td div[role=progressbar]').exists()).toBeFalsy();
    expect(wrapper.find('tbody tr td p').text()).toMatch('data_table.no_data');
  });
});

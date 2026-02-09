import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import AssetBalances from '@/components/AssetBalances.vue';

describe('assetBalances.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof AssetBalances>>;
  beforeEach(() => {
    const pinia = createCustomPinia();
    setActivePinia(pinia);
    wrapper = mount(AssetBalances, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
      },
      props: {
        balances: [],
      },
    });
  });

  afterEach(() => {
    wrapper.unmount();
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

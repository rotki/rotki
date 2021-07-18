import { mount, Wrapper } from '@vue/test-utils';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import store from '@/store/store';
import { GeneralAccount } from '@/typing/types';

Vue.use(Vuetify);

describe('AccountDisplay.vue', () => {
  let wrapper: Wrapper<AccountDisplay>;

  const account: GeneralAccount = {
    chain: 'ETH',
    address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    label: 'Test Account',
    tags: []
  };

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(AccountDisplay, {
      store,
      vuetify,
      stubs: ['v-tooltip', 'asset-icon'],
      propsData: {
        account
      }
    });
  }

  beforeEach(() => {
    store.dispatch('session/logout');
    wrapper = createWrapper();
  });

  test('does not blur anything by default', async () => {
    expect(wrapper.find('.blur-content').exists()).toBe(false);
  });

  test('blurs address on privacy mode', async () => {
    store.commit('session/privacyMode', true);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.blur-content').exists()).toBe(true);
  });
});

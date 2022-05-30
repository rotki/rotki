import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import store from '@/store/store';
import '../../i18n';

Vue.use(Vuetify);

describe('AccountDisplay.vue', () => {
  let wrapper: Wrapper<any>;

  const account: GeneralAccount = {
    chain: Blockchain.ETH,
    address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    label: 'Test Account',
    tags: []
  };

  function createWrapper() {
    const vuetify = new Vuetify();
    const pinia = createPinia();
    setActivePinia(pinia);
    return mount(AccountDisplay, {
      store,
      pinia,
      provide: {
        'vuex-store': store
      },
      vuetify,
      stubs: {
        VTooltip: {
          template:
            '<span><slot name="activator"/><slot v-if="!disabled"/></span>',
          props: {
            disabled: { type: Boolean }
          }
        },
        AssetIcon: true
      },
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
    store.commit('session/privacyMode', 1);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.blur-content').exists()).toBe(true);
  });
});

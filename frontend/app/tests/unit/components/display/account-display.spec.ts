import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { mount, Wrapper } from '@vue/test-utils';
import { set } from '@vueuse/core';
import {
  createPinia,
  Pinia,
  PiniaVuePlugin,
  setActivePinia,
  storeToRefs
} from 'pinia';
import Vue from 'vue';
import Vuetify from 'vuetify';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import '../../i18n';
import { useSessionStore } from '@/store/session';
import { PrivacyMode } from '@/store/session/types';
import { useSessionSettingsStore } from '@/store/settings/session';

Vue.use(Vuetify);
Vue.use(PiniaVuePlugin);

describe('AccountDisplay.vue', () => {
  let wrapper: Wrapper<any>;
  let pinia: Pinia;

  const account: GeneralAccount = {
    chain: Blockchain.ETH,
    address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
    label: 'Test Account',
    tags: []
  };

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(AccountDisplay, {
      pinia,
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

  beforeEach(async () => {
    pinia = createPinia();
    setActivePinia(pinia);
    await useSessionStore().logout();
    wrapper = createWrapper();
  });

  test('does not blur anything by default', async () => {
    expect(wrapper.find('.blur-content').exists()).toBe(false);
  });

  test('blurs address on privacy mode', async () => {
    const { privacyMode } = storeToRefs(useSessionSettingsStore());
    set(privacyMode, PrivacyMode.SEMI_PRIVATE);
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.blur-content').exists()).toBe(true);
  });
});

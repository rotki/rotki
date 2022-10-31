import { GeneralAccount } from '@rotki/common/lib/account';
import { Blockchain } from '@rotki/common/lib/blockchain';
import { mount, Wrapper } from '@vue/test-utils';
import { createPinia, Pinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import { useSessionStore } from '@/store/session';
import { PrivacyMode } from '@/store/session/types';
import { useSessionSettingsStore } from '@/store/settings/session';

vi.mock('@/services/rotkehlchen-api', () => ({
  assets: {
    assetImageUrl: vi.fn()
  }
}));
vi.mock('@/services/websocket/websocket-service');

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
    useSessionSettingsStore().update({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await wrapper.vm.$nextTick();
    expect(wrapper.find('.blur-content').exists()).toBe(true);
  });
});

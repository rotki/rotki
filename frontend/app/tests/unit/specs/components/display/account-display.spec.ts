import { Blockchain } from '@rotki/common/lib/blockchain';
import { type Wrapper, mount } from '@vue/test-utils';
import { type Pinia, createPinia, setActivePinia } from 'pinia';
import Vuetify from 'vuetify';
import AccountDisplay from '@/components/display/AccountDisplay.vue';
import { PrivacyMode } from '@/types/session';
import type { Account } from '@rotki/common/lib/account';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: () => ({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

describe('accountDisplay.vue', () => {
  let wrapper: Wrapper<any>;
  let pinia: Pinia;

  const account: Account = {
    chain: Blockchain.ETH,
    address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
  };

  function createWrapper() {
    const vuetify = new Vuetify();
    return mount(AccountDisplay, {
      pinia,
      vuetify,
      stubs: {
        AssetIcon: true,
      },
      propsData: {
        account,
      },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    wrapper = createWrapper();
  });

  it('does not blur anything by default', () => {
    expect(wrapper.find('.blur').exists()).toBe(false);
  });

  it('blurs address on privacy mode', async () => {
    useSessionSettingsStore().update({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await nextTick();
    expect(wrapper.find('.blur').exists()).toBe(true);
  });
});

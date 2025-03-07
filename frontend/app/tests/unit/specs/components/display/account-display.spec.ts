import AccountDisplay from '@/components/display/AccountDisplay.vue';
import { useSessionSettingsStore } from '@/store/settings/session';
import { PrivacyMode } from '@/types/session';
import { type Account, Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/composables/api/assets/icon', () => ({
  useAssetIconApi: () => ({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

describe('accountDisplay.vue', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountDisplay>>;
  let pinia: Pinia;

  const account: Account = {
    chain: Blockchain.ETH,
    address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
  };

  function createWrapper() {
    return mount(AccountDisplay, {
      global: {
        stubs: {
          AssetIcon: true,
        },
        plugins: [pinia],
      },
      props: {
        account,
      },
    });
  }

  beforeEach(() => {
    pinia = createPinia();
    setActivePinia(pinia);
    wrapper = createWrapper();
  });

  afterEach(() => {
    wrapper.unmount();
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

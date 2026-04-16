import { type Account, Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { createPinia, type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { PrivacyMode } from '@/modules/session/types';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import AccountDisplay from '@/modules/shell/components/display/AccountDisplay.vue';

vi.mock('@/modules/assets/api/use-asset-icon-api', (): Record<string, unknown> => ({
  useAssetIconApi: (): { assetImageUrl: ReturnType<typeof vi.fn> } => ({
    assetImageUrl: vi.fn(),
  }),
}));
vi.mock('@/services/websocket/websocket-service');

describe('account-display', () => {
  let wrapper: VueWrapper<InstanceType<typeof AccountDisplay>>;
  let pinia: Pinia;

  const account: Account = {
    chain: Blockchain.ETH,
    address: '0x52bc44d5378309EE2abF1539BF71dE1b7d7bE3b5',
  };

  function createWrapper(): VueWrapper<InstanceType<typeof AccountDisplay>> {
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

  beforeEach((): void => {
    pinia = createPinia();
    setActivePinia(pinia);
    wrapper = createWrapper();
  });

  afterEach((): void => {
    wrapper.unmount();
  });

  it('should not blur anything by default', () => {
    expect(wrapper.find('.blur').exists()).toBe(false);
  });

  it('should blur address on privacy mode', async () => {
    useFrontendSettingsStore().update({ privacyMode: PrivacyMode.SEMI_PRIVATE });
    await nextTick();
    expect(wrapper.find('.blur').exists()).toBe(true);
  });
});

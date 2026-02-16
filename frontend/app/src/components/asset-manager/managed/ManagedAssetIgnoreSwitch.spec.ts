import { createCustomPinia } from '@test/utils/create-pinia';
import { libraryDefaults } from '@test/utils/provide-defaults';
import { mount, type VueWrapper } from '@vue/test-utils';
import { type Pinia, setActivePinia } from 'pinia';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import ManagedAssetIgnoreSwitch from './ManagedAssetIgnoreSwitch.vue';

vi.mock('@/store/assets/ignored', () => ({
  useIgnoredAssetsStore: vi.fn().mockReturnValue({
    useIsAssetIgnored: (): Ref<boolean> => ref(false),
  }),
}));

vi.mock('@/store/assets/whitelisted', () => ({
  useWhitelistedAssetsStore: vi.fn().mockReturnValue({
    useIsAssetWhitelisted: (): Ref<boolean> => ref(false),
  }),
}));

describe('managedAssetIgnoreSwitch', () => {
  let wrapper: VueWrapper;
  let pinia: Pinia;

  beforeEach(() => {
    pinia = createCustomPinia();
    setActivePinia(pinia);
  });

  afterEach(() => {
    wrapper.unmount();
  });

  function createWrapper(asset: { identifier: string; assetType?: string | null; protocol?: string | null }): VueWrapper {
    return mount(ManagedAssetIgnoreSwitch, {
      global: {
        plugins: [pinia],
        provide: libraryDefaults,
      },
      props: { asset },
    });
  }

  it('shows spam/whitelist menu for EVM token assets', () => {
    wrapper = createWrapper({ identifier: 'eip155:1/erc20:0x1234', assetType: 'evm token' });
    expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(true);
  });

  it('shows spam/whitelist menu for Solana token assets', () => {
    wrapper = createWrapper({ identifier: 'solana:SOL/spl:TokenAddr', assetType: 'solana token' });
    expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(true);
  });

  it('hides spam/whitelist menu for custom assets', () => {
    wrapper = createWrapper({ identifier: 'my-custom-asset', assetType: 'custom asset' });
    expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(false);
  });

  it('hides spam/whitelist menu for assets with no type', () => {
    wrapper = createWrapper({ identifier: 'BTC', assetType: null });
    expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(false);
  });

  it('hides spam/whitelist menu for unknown asset types', () => {
    wrapper = createWrapper({ identifier: 'some-asset', assetType: 'other type' });
    expect(wrapper.findComponent({ name: 'RuiMenu' }).exists()).toBe(false);
  });
});

import { mockT } from '@test/i18n';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import PoolIcon from '@/modules/dashboard/liquidity-pools/PoolIcon.vue';
import { PoolType } from '@/modules/dashboard/liquidity-pools/types';

const AppImage = {
  name: 'AppImage',
  props: ['src', 'size'],
  template: '<img data-testid="app-image" :src="src" />',
};

const AssetIcon = {
  name: 'AssetIcon',
  props: ['identifier', 'size', 'circle', 'padding', 'showChain', 'hideProtocol'],
  template: '<div data-testid="asset-icon" :data-identifier="identifier" />',
};

const AssetDetails = {
  name: 'AssetDetails',
  props: ['asset', 'display', 'actions'],
  template: '<div data-testid="asset-details" :data-identifier="asset" />',
};

const ASSETS = ['ETH', 'USDC', 'LINK'];
const MORE_LABEL = mockT('modules.dashboard.liquidity_pools.pool_icon.more', { count: 2 });

describe('poolIcon', () => {
  function createWrapper(assets: string[]): VueWrapper {
    return mount(PoolIcon, {
      attachTo: document.body,
      global: { stubs: { AppImage, AssetDetails, AssetIcon } },
      props: { assets, type: PoolType.UNISWAP_V2 },
    });
  }

  function listedAssets(): string[] {
    return Array.from(
      document.body.querySelectorAll(`[role="dialog"][aria-label="${MORE_LABEL}"] [data-testid="asset-details"]`),
      row => row.getAttribute('data-identifier') ?? '',
    );
  }

  it('should draw both assets of a pair side by side, with no menu', () => {
    const wrapper = createWrapper(['ETH', 'USDC']);

    expect(wrapper.findAll('[data-testid="asset-icon"]').map(icon => icon.attributes('data-identifier'))).toStrictEqual(['ETH', 'USDC']);
    expect(wrapper.find('[data-testid="pool-icon-more"]').exists()).toBe(false);
  });

  it('should count the assets past the first on the more button', () => {
    expect(createWrapper(ASSETS).find('[data-testid="pool-icon-more"]').text()).toBe('+2');
  });

  it('should offer the more button to the keyboard as a native button named after the hidden assets', () => {
    const button = createWrapper(ASSETS).find('[data-testid="pool-icon-more"]');

    expect(button.element.tagName).toBe('BUTTON');
    expect(button.attributes('type')).toBe('button');
    expect(button.attributes('aria-label')).toBe(MORE_LABEL);
  });

  it('should list every asset of the pool in a dialog named like the button once it is clicked', async () => {
    const wrapper = createWrapper(ASSETS);

    await wrapper.find('[data-testid="pool-icon-more"]').trigger('click');

    await vi.waitFor(() => expect(listedAssets()).toStrictEqual(ASSETS));
  });
});

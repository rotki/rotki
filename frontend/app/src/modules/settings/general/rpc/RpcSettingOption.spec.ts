import { Blockchain } from '@rotki/common';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import RpcSettingOption from '@/modules/settings/general/rpc/RpcSettingOption.vue';
import { RpcSettingKey } from '@/modules/settings/general/rpc/use-rpc-settings-tabs';

vi.mock('@/modules/history/LocationDisplay.vue', () => ({
  default: {
    name: 'LocationDisplay',
    props: ['identifier', 'horizontal', 'size', 'openDetails'],
    template: '<span data-testid="location-display">{{ identifier }}</span>',
  },
}));

vi.mock('@/modules/shell/components/AppImage.vue', () => ({
  default: {
    name: 'AppImage',
    props: ['src', 'size', 'contain'],
    template: '<img data-testid="app-image" :src="src" />',
  },
}));

function mountOption(props: InstanceType<typeof RpcSettingOption>['$props']): VueWrapper {
  return mount(RpcSettingOption, { props });
}

describe('rpcSettingOption', () => {
  it('should render LocationDisplay for chain-backed tabs', () => {
    const wrapper = mountOption({ tab: { chain: Blockchain.ETH } });
    const display = wrapper.find('[data-testid=location-display]');
    expect(display.exists()).toBe(true);
    expect(display.text()).toBe(Blockchain.ETH);
    expect(wrapper.find('[data-testid=app-image]').exists()).toBe(false);
  });

  it('should render AppImage and name for custom tabs', () => {
    const wrapper = mountOption({
      tab: {
        id: 'eth_consensus_layer',
        image: '/img/beacon.svg',
        name: 'ETH Beacon Node',
        setting: RpcSettingKey.BEACON,
      },
    });
    const image = wrapper.find('[data-testid=app-image]');
    expect(image.exists()).toBe(true);
    expect(image.attributes('src')).toBe('/img/beacon.svg');
    expect(wrapper.text()).toContain('ETH Beacon Node');
    expect(wrapper.find('[data-testid=location-display]').exists()).toBe(false);
  });

  it('should not render a group header by default', () => {
    const wrapper = mountOption({ tab: { chain: Blockchain.ETH } });
    expect(wrapper.text()).not.toContain('OTHER');
  });

  it('should render the supplied group label above the row', () => {
    const wrapper = mountOption({
      tab: { chain: Blockchain.SOLANA },
      groupLabel: 'Other endpoints',
    });
    expect(wrapper.text()).toContain('Other endpoints');
  });
});

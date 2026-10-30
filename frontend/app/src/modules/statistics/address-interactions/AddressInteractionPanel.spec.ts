import type { AddressInteraction } from './address-interaction-types';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { createAddressInteractionGraph, type InteractionConnection } from './address-interaction-graph';
import AddressInteractionPanel from './AddressInteractionPanel.vue';

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName: (): undefined => undefined }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string): string => chain }),
}));

function connections(size: number): InteractionConnection[] {
  return createAddressInteractionGraph(Array.from({ length: size }, (_, index): AddressInteraction => ({
    chain: 'eth',
    source: 'hub',
    target: `leaf-${String(index).padStart(3, '0')}`,
    txHash: `0x${index}`,
  }))).connections;
}

function createWrapper(items: InteractionConnection[]): VueWrapper<InstanceType<typeof AddressInteractionPanel>> {
  return mount(AddressInteractionPanel, {
    global: {
      stubs: {
        AddressInteractionDetails: true,
        HashLink: true,
        LocationIcon: true,
        RuiButton: { emits: ['click'], template: '<button type="button" v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>' },
        RuiIcon: true,
      },
    },
    props: { connectionLabel: (connection: InteractionConnection): string => connection.id, connections: items },
  });
}

describe('address interaction panel', () => {
  it('should render the first page of connections and reveal the rest on demand', async () => {
    const wrapper = createWrapper(connections(60));
    const showMore = wrapper.get('[data-testid=interaction-connection-show-more]');

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(50);
    expect(showMore.text()).toContain('10');

    await showMore.trigger('click');

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(60);
    expect(wrapper.find('[data-testid=interaction-connection-show-more]').exists()).toBe(false);
  });

  it('should keep the revealed connections after returning from a connection\'s details', async () => {
    const items = connections(60);
    const wrapper = createWrapper(items);
    await wrapper.get('[data-testid=interaction-connection-show-more]').trigger('click');

    await wrapper.setProps({ selectedConnection: items[55] });
    expect(wrapper.find('[data-testid=interaction-connection-list]').exists()).toBe(false);
    await wrapper.setProps({ selectedConnection: undefined });

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(60);
  });

  it('should start from the first page again when the connections change', async () => {
    const wrapper = createWrapper(connections(60));
    await wrapper.get('[data-testid=interaction-connection-show-more]').trigger('click');

    await wrapper.setProps({ connections: connections(70) });

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(50);
  });
});

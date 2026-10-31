import type { AddressInteraction } from './address-interaction-types';
import { ClickButtonStub } from '@test/utils/address-interactions';
import { mount, type VueWrapper } from '@vue/test-utils';
import { describe, expect, it, vi } from 'vitest';
import { nextTick } from 'vue';
import AddressInteractionPanel from './AddressInteractionPanel.vue';
import { type AddressInteractionExplorer, useAddressInteractionExplorer } from './use-address-interaction-explorer';

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName: (): undefined => undefined, getEnsName: (): null => null }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string): string => chain }),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): object => ({ scrambleAddress: (address: string): string => address, scrambleData: ref<boolean>(false) }),
}));

function star(size: number): AddressInteraction[] {
  return Array.from({ length: size }, (_, index): AddressInteraction => ({
    chain: 'eth',
    source: 'hub',
    target: `leaf-${String(index).padStart(3, '0')}`,
    txHash: `0x${index}`,
  }));
}

function createWrapper(interactions: AddressInteraction[]): { wrapper: VueWrapper<InstanceType<typeof AddressInteractionPanel>>; explorer: AddressInteractionExplorer; source: Ref<AddressInteraction[]> } {
  const source = ref<AddressInteraction[]>(interactions);
  const explorer = useAddressInteractionExplorer(source);
  const wrapper = mount(AddressInteractionPanel, {
    global: {
      stubs: {
        AddressInteractionDetails: { props: ['connection'], template: '<div data-testid="interaction-details" />' },
        EnsAvatar: true,
        HashLink: true,
        LocationIcon: true,
        RuiButton: ClickButtonStub,
        RuiIcon: true,
      },
    },
    props: { explorer },
  });
  return { explorer, source, wrapper };
}

describe('address interaction panel', () => {
  it('should render the first page of connections and reveal the rest on demand', async () => {
    const { wrapper } = createWrapper(star(60));
    const showMore = wrapper.get('[data-testid=interaction-connection-show-more]');

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(50);
    expect(showMore.text()).toContain('10');

    await showMore.trigger('click');

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(60);
    expect(wrapper.find('[data-testid=interaction-connection-show-more]').exists()).toBe(false);
  });

  it('should keep the revealed connections after returning from a connection\'s details', async () => {
    const { explorer, wrapper } = createWrapper(star(60));
    await wrapper.get('[data-testid=interaction-connection-show-more]').trigger('click');

    await wrapper.findAll('[data-testid=interaction-connection]')[55].trigger('click');
    expect(wrapper.find('[data-testid=interaction-details]').exists()).toBe(true);
    explorer.clearConnection();
    await nextTick();

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(60);
  });

  it('should start from the first page again when the connections change', async () => {
    const { source, wrapper } = createWrapper(star(60));
    await wrapper.get('[data-testid=interaction-connection-show-more]').trigger('click');

    set(source, star(70));
    await nextTick();

    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(50);
  });

  it('should list clusters with their weakest link and focus one on click', async () => {
    const { explorer, wrapper } = createWrapper([
      { chain: 'eth', source: 'a', target: 'b', txHash: '0x1' },
      { chain: 'eth', source: 'b', target: 'c', txHash: '0x2' },
      { chain: 'eth', source: 'b', target: 'c', txHash: '0x3' },
      { chain: 'eth', source: 'x', target: 'y', txHash: '0x4' },
    ]);
    const clusters = wrapper.findAll('[data-testid=interaction-cluster]');

    expect(clusters).toHaveLength(2);
    expect(clusters[0].get('[data-testid=interaction-cluster-weakest]').findAll('[data-testid=interaction-address]').map(address => address.text())).toEqual(['a', 'b']);

    await clusters[0].trigger('click');

    expect(get(explorer.selectedClusterIndex)).toBe(0);
    expect([...(get(explorer.focus)?.nodeIds ?? [])]).toEqual(['a', 'b', 'c']);
  });

  it('should offer path finding and hiding for a selected address, and show the path once a target is picked', async () => {
    const { explorer, wrapper } = createWrapper([
      { chain: 'eth', source: 'a', target: 'b', txHash: '0x1' },
      { chain: 'eth', source: 'b', target: 'c', txHash: '0x2' },
    ]);
    const [a, , c] = get(explorer.scene).nodes;
    explorer.selectNode(a);
    await nextTick();
    expect(wrapper.find('[data-testid=interaction-clusters]').exists()).toBe(false);

    await wrapper.get('[data-testid=interaction-find-path]').trigger('click');
    explorer.selectNode(c);
    await nextTick();

    expect(wrapper.findAll('[data-testid=interaction-path-step]').map(step => step.text())).toEqual([
      expect.stringContaining('a'),
      expect.stringContaining('b'),
      'c',
    ]);

    await wrapper.get('[data-testid=interaction-path-back]').trigger('click');
    await wrapper.get('[data-testid=interaction-hide-node]').trigger('click');

    expect(get(explorer.scene).nodes.map(node => node.id)).toEqual(['b', 'c']);
    expect(get(explorer.stats).hidden).toBe(1);
  });
});

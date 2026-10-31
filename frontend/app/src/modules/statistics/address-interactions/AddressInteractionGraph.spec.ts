import type { ECElementEvent } from 'echarts';
import type { AddressInteraction } from './address-interaction-types';
import { ClickButtonStub, graphSeries, interaction, OTHER, SOURCE, TARGET } from '@test/utils/address-interactions';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Router, useRouter } from 'vue-router';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import AddressInteractionGraph from './AddressInteractionGraph.vue';

const { getAddressName, scrambleAddress } = vi.hoisted(() => ({
  getAddressName: vi.fn<(address: string, chain?: string) => string | undefined>(),
  scrambleAddress: vi.fn((address: string): string => address),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): object => ({
    scrambleAddress,
    scrambleData: ref(false),
    scrambleIdentifier: (value: string): string => value,
    shouldShowAmount: ref(true),
  }),
}));

vi.mock('vue-echarts', () => ({
  default: { emits: ['click'], name: 'VChart', props: ['option'], template: '<div />' },
}));

vi.mock('./use-node-avatars', () => ({
  useNodeAvatars: (): object => ref(new Map()),
}));

vi.mock('@/modules/statistics/use-graph', () => ({
  useGraph: (): object => ({ baseColor: ref('#7e4a3b'), secondaryColor: ref('#3f3f46') }),
}));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): object => ref({}),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({
    getAddressName,
    getAddressNameSource: (): undefined => undefined,
    getEnsName: (): null => null,
  }),
}));

vi.mock('@/modules/balances/blockchain/use-blockchain-account-data', () => ({
  useBlockchainAccountData: (): object => ({ useAccountTags: (): Ref<string[]> => ref([]) }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getChainName: (chain: string): string => chain,
    matchChain: (value: string): string | undefined => ['eth', 'ethereum'].includes(value) ? 'eth' : undefined,
  }),
}));

vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): object => ({ tradeLocations: ref([{ identifier: 'optimism' }, { identifier: 'ethereum' }]) }),
}));

function createWrapper(interactions: readonly AddressInteraction[]): VueWrapper<InstanceType<typeof AddressInteractionGraph>> {
  return mount(AddressInteractionGraph, {
    global: {
      stubs: {
        AddressDeleteButton: true,
        AddressEditButton: true,
        EnsAvatar: true,
        InlineCopyButton: true,
        LinkButton: true,
        LocationIcon: true,
        LocationLabelSelector: true,
        RuiButton: ClickButtonStub,
        RuiSlider: { emits: ['update:modelValue'], name: 'RuiSlider', props: ['modelValue', 'max'], template: '<div data-testid="slider" />' },
        TagDisplay: true,
      },
    },
    props: { interactions },
  });
}

async function searchAddress(wrapper: VueWrapper, address: string): Promise<void> {
  wrapper.getComponent(LocationLabelSelector).vm.$emit('update:modelValue', address);
  await nextTick();
}

function transactionLinks(wrapper: VueWrapper): VueWrapper<InstanceType<typeof HashLink>>[] {
  return wrapper.findAllComponents(HashLink).filter(link => link.props('type') === 'transaction');
}

function nodeIds(wrapper: VueWrapper): unknown[] {
  return (graphSeries(wrapper).data ?? []).map(item => typeof item === 'object' && item !== null && 'id' in item ? item.id : undefined);
}

function linkOpacities(wrapper: VueWrapper): unknown[] {
  return graphSeries(wrapper).links?.map(link => link.lineStyle?.opacity) ?? [];
}

async function clickNode(wrapper: VueWrapper, address: string): Promise<void> {
  const dataIndex = nodeIds(wrapper).indexOf(address);
  assert(dataIndex >= 0);
  wrapper.getComponent({ name: 'VChart' }).vm.$emit('click', createMock<ECElementEvent>({ dataIndex, dataType: 'node' }));
  await nextTick();
}

function selectedAddress(wrapper: VueWrapper): unknown {
  return wrapper.get('[data-testid=interaction-panel-node]').findComponent(HashLink).props('text');
}

function listedConnections(wrapper: VueWrapper): number {
  return wrapper.findAll('[data-testid=interaction-connection]').length;
}

describe('address interaction graph', () => {
  beforeEach(() => {
    scrambleAddress.mockImplementation(address => address);
    getAddressName.mockReturnValue(undefined);
  });

  it('should draw one connection per pair and break its transactions down by chain', async () => {
    const wrapper = createWrapper([
      interaction(),
      interaction('eth', '0xsecond-transaction', TARGET, SOURCE),
      interaction('optimism', '0xoptimism-transaction'),
      interaction('eth', '0xself', SOURCE, SOURCE),
    ]);

    expect(graphSeries(wrapper).links).toHaveLength(1);
    expect(listedConnections(wrapper)).toBe(1);
    expect(wrapper.get('[data-testid=interaction-connection-count]').text()).toBe('address_interactions.tx_count::3');

    await wrapper.get('[data-testid=interaction-connection]').trigger('click');

    const sections = wrapper.findAll('[data-testid=interaction-chain-activity]');
    expect(sections.map(section => section.attributes('data-chain'))).toEqual(['eth', 'optimism']);
    expect(transactionLinks(wrapper).map(link => ({ chain: link.props('location'), hash: link.props('text') }))).toEqual([
      { chain: 'eth', hash: '0xeth-transaction' },
      { chain: 'eth', hash: '0xsecond-transaction' },
      { chain: 'optimism', hash: '0xoptimism-transaction' },
    ]);
    expect(transactionLinks(wrapper)[2].getComponent({ name: 'LinkButton' }).props('base')).toBe('https://optimistic.etherscan.io/tx/');
  });

  it('should page a chain\'s transactions and start over on the first page when another pair is opened from the graph', async () => {
    const many = (target: string): AddressInteraction[] => Array.from({ length: 60 }, (_, index) => interaction('eth', `${target}-${index}`, SOURCE, target));
    const wrapper = createWrapper([...many(TARGET), ...many(OTHER)]);
    await wrapper.findAll('[data-testid=interaction-connection]')[0].trigger('click');
    expect(transactionLinks(wrapper)).toHaveLength(50);
    await wrapper.get('[data-testid=interaction-tx-show-more]').trigger('click');
    expect(transactionLinks(wrapper)).toHaveLength(60);

    wrapper.getComponent({ name: 'VChart' }).vm.$emit('click', createMock<ECElementEvent>({ dataIndex: 1, dataType: 'edge' }));
    await nextTick();

    expect(wrapper.findComponent(HashLink).props('text')).toBe(SOURCE);
    expect(transactionLinks(wrapper).map(link => link.props('text'))).toContain(`${OTHER}-0`);
    expect(transactionLinks(wrapper)).toHaveLength(50);
  });

  it('should open history events filtered to one chain of the pair, or a single transaction', async () => {
    const push = vi.fn<Router['push']>().mockResolvedValue(undefined);
    vi.mocked(useRouter).mockReturnValue(createMock<Router>({ push }));
    const wrapper = createWrapper([interaction(), interaction('eth', '0xsecond-transaction'), interaction('optimism', '0xop')]);
    await wrapper.get('[data-testid=interaction-connection]').trigger('click');

    await wrapper.findAll('[data-testid=interaction-history-link]')[0].trigger('click');
    expect(push).toHaveBeenLastCalledWith({
      name: '/history/events/',
      query: { location: 'ethereum', txRefs: ['0xeth-transaction', '0xsecond-transaction'] },
    });

    await wrapper.findAll('[data-testid=interaction-tx-history]')[1].trigger('click');
    expect(push).toHaveBeenLastCalledWith({ name: '/history/events/', query: { location: 'ethereum', txRefs: ['0xsecond-transaction'] } });
    vi.mocked(useRouter).mockReset();
  });

  it('should select an address from the graph and list only its counterparts', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xother', TARGET, OTHER)]);

    await clickNode(wrapper, TARGET);

    expect(selectedAddress(wrapper)).toBe(TARGET);
    const listed = wrapper.findAll('[data-testid=interaction-connection-label]').map(label => label.text());
    expect(listed).toEqual(['0x111111...111111', '0x333333...333333']);

    await wrapper.get('[data-testid=interaction-panel-clear-node]').trigger('click');
    expect(wrapper.find('[data-testid=interaction-panel-node]').exists()).toBe(false);
  });

  it('should grey out connections on other chains instead of removing them, keeping the selection', async () => {
    const wrapper = createWrapper([interaction(), interaction('optimism', '0xop', TARGET, OTHER)]);
    await clickNode(wrapper, TARGET);

    await wrapper.get('[data-testid=interaction-chain][data-chain=optimism]').trigger('click');

    expect(nodeIds(wrapper)).toHaveLength(3);
    expect(linkOpacities(wrapper)).toEqual([0.07, 0.6]);
    expect(selectedAddress(wrapper)).toBe(TARGET);
    expect(listedConnections(wrapper)).toBe(1);
    expect(wrapper.get('[data-testid=interaction-muted]').text()).toContain('1');

    await wrapper.get('[data-testid=interaction-all-chains]').trigger('click');
    expect(listedConnections(wrapper)).toBe(2);
  });

  it('should grey out pairs below the minimum number of shared transactions', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xsecond'), interaction('eth', '0xother', TARGET, OTHER)]);
    const slider = wrapper.getComponent({ name: 'RuiSlider' });
    expect(slider.props('max')).toBe(2);

    slider.vm.$emit('update:modelValue', 2);
    await nextTick();

    expect(linkOpacities(wrapper)).toEqual([0.6, 0.07]);
    expect(listedConnections(wrapper)).toBe(1);

    await wrapper.get('[data-testid=interaction-reset-filters]').trigger('click');
    expect(listedConnections(wrapper)).toBe(2);
  });

  it('should say so on the canvas when the filters leave no pair, and reset from there', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xsecond'), interaction('optimism', '0xop', TARGET, OTHER)]);
    wrapper.getComponent({ name: 'RuiSlider' }).vm.$emit('update:modelValue', 2);
    await nextTick();
    expect(wrapper.find('[data-testid=interaction-filtered-out]').exists()).toBe(false);

    await wrapper.get('[data-testid=interaction-chain][data-chain=optimism]').trigger('click');
    const overlay = wrapper.get('[data-testid=interaction-filtered-out]');

    await overlay.get('button').trigger('click');
    expect(wrapper.find('[data-testid=interaction-filtered-out]').exists()).toBe(false);
    expect(listedConnections(wrapper)).toBe(2);
  });

  it('should select a searched address without filtering the graph down to it', async () => {
    getAddressName.mockImplementation((address, chain) => address === SOURCE && chain === 'optimism' ? 'Savings' : undefined);
    const wrapper = createWrapper([interaction(), interaction('optimism'), interaction('eth', '0xother', TARGET, OTHER)]);
    expect(wrapper.getComponent(LocationLabelSelector).props('options')).toEqual([
      { location: 'optimism', locationLabel: SOURCE },
      { location: 'eth', locationLabel: TARGET },
      { location: 'eth', locationLabel: OTHER },
    ]);

    await searchAddress(wrapper, OTHER);

    expect(graphSeries(wrapper).links).toHaveLength(2);
    expect(selectedAddress(wrapper)).toBe(OTHER);
    expect(listedConnections(wrapper)).toBe(1);

    await wrapper.get('[data-testid=clear-interaction-selection]').trigger('click');
    expect(wrapper.getComponent(LocationLabelSelector).props('modelValue')).toBe('');
  });

  it('should hide an address from the graph until the user shows hidden addresses again', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xother', TARGET, OTHER)]);
    await clickNode(wrapper, OTHER);

    await wrapper.get('[data-testid=interaction-hide-node]').trigger('click');

    expect(nodeIds(wrapper)).toEqual([SOURCE, TARGET]);
    expect(listedConnections(wrapper)).toBe(1);

    await wrapper.get('[data-testid=interaction-show-hidden]').trigger('click');
    expect(nodeIds(wrapper)).toEqual([SOURCE, TARGET, OTHER]);
  });

  it('should ask for a second address and then trace the path to it', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xother', TARGET, OTHER)]);
    await clickNode(wrapper, SOURCE);
    await wrapper.get('[data-testid=interaction-find-path]').trigger('click');
    expect(wrapper.find('[data-testid=interaction-path-picking]').exists()).toBe(true);

    await clickNode(wrapper, OTHER);

    expect(wrapper.find('[data-testid=interaction-path-picking]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid=interaction-path-step]')).toHaveLength(3);
    expect(linkOpacities(wrapper)).toEqual([1, 1]);
  });

  it('should scramble labels, accessible names and selected hashes', async () => {
    scrambleAddress.mockImplementation(() => 'hidden-address');
    const wrapper = createWrapper([interaction()]);

    expect(wrapper.get('[data-testid=interaction-connection]').attributes('aria-label')).not.toContain(TARGET);
    expect(wrapper.text()).not.toContain(SOURCE);
    expect(wrapper.text()).not.toContain(TARGET);

    await wrapper.get('[data-testid=interaction-connection]').trigger('click');

    expect(wrapper.get('[data-testid=interaction-details]').text()).not.toContain('0xeth-transaction');
    expect(wrapper.get('[data-testid=interaction-details]').text()).toContain('hidden-address');
  });

  it('should discard a selection when refreshed interactions remove it', async () => {
    const wrapper = createWrapper([interaction()]);
    await wrapper.get('[data-testid=interaction-connection]').trigger('click');
    expect(transactionLinks(wrapper)).toHaveLength(1);

    await wrapper.setProps({ interactions: [interaction('solana', 'SolanaSignature', 'SolanaAddressA', 'SolanaAddressB')] });

    expect(wrapper.find('[data-testid=interaction-details]').exists()).toBe(false);
    expect(listedConnections(wrapper)).toBe(1);
  });
});

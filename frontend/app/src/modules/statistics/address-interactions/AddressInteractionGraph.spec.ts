import type { AddressInteraction } from './address-interaction-types';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type Router, useRouter } from 'vue-router';
import LocationLabelSelector from '@/modules/history/LocationLabelSelector.vue';
import HashLink from '@/modules/shell/components/HashLink.vue';
import { createAddressInteractionGraph } from './address-interaction-graph';
import AddressInteractionConnectionList from './AddressInteractionConnectionList.vue';
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

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: (): object => ref({}),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({
    getAddressName,
    getAddressNameSource: (): undefined => undefined,
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

const SOURCE = '0x1111111111111111111111111111111111111111';
const TARGET = '0x2222222222222222222222222222222222222222';
const OTHER = '0x3333333333333333333333333333333333333333';

function interaction(chain = 'eth', txHash = '0xeth-transaction', source = SOURCE, target = TARGET): AddressInteraction {
  return { chain, source, target, txHash };
}

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
        RuiButton: { emits: ['click'], template: '<button v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>' },
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

describe('address interaction graph', () => {
  beforeEach(() => {
    scrambleAddress.mockImplementation(address => address);
    getAddressName.mockReturnValue(undefined);
  });

  it('should aggregate unordered pairs and distinct transactions without merging chains', async () => {
    const wrapper = createWrapper([
      interaction(),
      interaction('eth', '0xsecond-transaction', TARGET, SOURCE),
      interaction('eth', '0xeth-transaction', TARGET, SOURCE),
      interaction('optimism', '0xoptimism-transaction'),
      interaction('eth', '0xself', SOURCE, SOURCE),
    ]);

    expect(wrapper.findAll('[data-testid=interaction-edge]')).toHaveLength(2);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(2);
    expect(wrapper.findAll('[data-testid=interaction-node]')).toHaveLength(2);
    const edges = wrapper.findAll('[data-testid=interaction-edge]');
    expect(edges[0].get('path').attributes('d')).not.toBe(edges[1].get('path').attributes('d'));
    expect(edges.map(edge => edge.get('text').text())).toEqual(['eth', 'optimism']);

    await wrapper.findAll('[data-testid=interaction-connection]')[0].trigger('click');

    const details = wrapper.get('[data-testid=interaction-details]');
    expect(details.text()).toContain('eth');
    expect(transactionLinks(wrapper).map(link => ({ chain: link.props('location'), hash: link.props('text') }))).toEqual([
      { chain: 'eth', hash: '0xeth-transaction' },
      { chain: 'eth', hash: '0xsecond-transaction' },
    ]);
    expect(transactionLinks(wrapper)[0].getComponent({ name: 'LinkButton' }).props()).toMatchObject({
      base: 'https://etherscan.io/tx/',
      text: '0xeth-transaction',
    });
  });

  it('should select one global address and explore its separate connections on every chain', async () => {
    const wrapper = createWrapper([
      interaction(),
      interaction('optimism', '0xoptimism-transaction'),
      interaction('eth', '0xother', TARGET, OTHER),
    ]);
    const sourceNode = wrapper.findAll('[data-testid=interaction-node]').find(node =>
      node.attributes('aria-label')?.includes(SOURCE),
    );

    assert(sourceNode);
    await sourceNode.trigger('keydown', { key: 'Enter' });
    expect(sourceNode.attributes('aria-pressed')).toBe('true');
    expect(wrapper.findAll('[data-testid=interaction-node]')).toHaveLength(3);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(2);
    const optimismConnection = wrapper.findAll('[data-testid=interaction-connection]').find(connection =>
      connection.attributes('aria-label')?.includes('optimism'),
    );
    assert(optimismConnection);
    await optimismConnection.trigger('click');
    expect(transactionLinks(wrapper).map(link => ({ chain: link.props('location'), hash: link.props('text') }))).toEqual([
      { chain: 'optimism', hash: '0xoptimism-transaction' },
    ]);
    expect(transactionLinks(wrapper)[0].getComponent({ name: 'LinkButton' }).props('base')).toBe('https://optimistic.etherscan.io/tx/');

    await wrapper.get('[data-testid=clear-interaction-selection]').trigger('click');
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(3);
    expect(transactionLinks(wrapper)).toHaveLength(0);
  });

  it('should keep the global address selected when filtering to another chain', async () => {
    const wrapper = createWrapper([interaction(), interaction('optimism')]);
    const sourceNode = wrapper.findAll('[data-testid=interaction-node]').find(node =>
      node.attributes('aria-label')?.includes(SOURCE),
    );
    assert(sourceNode);
    await sourceNode.trigger('click');
    await wrapper.get('[data-testid=interaction-chain][data-chain=optimism]').trigger('click');
    expect(wrapper.get('[data-testid=interaction-node][aria-pressed=true]').attributes('aria-label')).toContain(SOURCE);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(1);
    await wrapper.get('[data-testid=interaction-all-chains]').trigger('click');
    expect(wrapper.findAll('[data-testid=interaction-node]')).toHaveLength(2);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(2);
  });

  it('should suggest each address on the chain where it has a name, and find all its connections', async () => {
    getAddressName.mockImplementation((address, chain) => address === SOURCE && chain === 'optimism' ? 'Savings' : undefined);
    const wrapper = createWrapper([interaction(), interaction('optimism')]);
    expect(wrapper.getComponent(LocationLabelSelector).props('options')).toEqual([
      { location: 'optimism', locationLabel: SOURCE },
      { location: 'eth', locationLabel: TARGET },
    ]);
    await searchAddress(wrapper, SOURCE);
    expect(wrapper.findAll('[data-testid=interaction-node]')).toHaveLength(2);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(2);
    expect(wrapper.get('[data-testid=interaction-panel-node]').findComponent(HashLink).props('location')).toBe('optimism');
  });

  it('should restore the whole graph when the searched address is cleared', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xother', TARGET, OTHER)]);
    await searchAddress(wrapper, OTHER);
    expect(wrapper.findAll('[data-testid=interaction-edge]')).toHaveLength(1);

    await wrapper.get('[data-testid=interaction-panel-clear-node]').trigger('click');

    expect(wrapper.findAll('[data-testid=interaction-edge]')).toHaveLength(2);
    expect(wrapper.getComponent(LocationLabelSelector).props('modelValue')).toBe('');
  });

  it('should select a non-EVM connection from the SVG and use its transaction explorer', async () => {
    const wrapper = createWrapper([interaction('solana', '5SolanaSignature', 'SolanaAddressA', 'SolanaAddressB')]);

    await wrapper.get('[data-testid=interaction-edge]').trigger('keydown', { key: ' ' });

    expect(transactionLinks(wrapper)[0].props()).toMatchObject({
      location: 'solana',
      text: '5SolanaSignature',
      type: 'transaction',
    });
    expect(transactionLinks(wrapper)[0].getComponent({ name: 'LinkButton' }).props('base')).toBe('https://solscan.io/tx/');
  });

  it('should scramble graph labels, accessible names, connection buttons and selected hashes', async () => {
    scrambleAddress.mockImplementation(() => 'hidden-address');
    const wrapper = createWrapper([interaction()]);

    expect(wrapper.get('[data-testid=interaction-node]').attributes('aria-label')).not.toContain(SOURCE);
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

    await wrapper.setProps({ interactions: [interaction('solana', 'SolanaSignature')] });

    expect(transactionLinks(wrapper)).toHaveLength(0);
    expect(wrapper.find('[data-testid=interaction-details]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(1);
  });

  it('should list strongest connections first with their transaction counts', () => {
    const wrapper = createWrapper([
      interaction('eth', '0xother', TARGET, OTHER),
      interaction(),
      interaction('eth', '0xsecond-transaction'),
    ]);
    const rows = wrapper.findAll('[data-testid=interaction-connection]');
    expect(rows[0].attributes('aria-label')).toContain(SOURCE);
    expect(rows.map(row => row.get('[data-testid=interaction-connection-count]').text())).toEqual([
      'address_interactions.tx_count::2',
      'address_interactions.tx_count::1',
    ]);
  });

  it('should state the selected address once and list only its counterparts', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xother', TARGET, OTHER)]);
    const targetNode = wrapper.findAll('[data-testid=interaction-node]').find(node =>
      node.attributes('aria-label')?.includes(TARGET),
    );
    assert(targetNode);
    await targetNode.trigger('click');

    const header = wrapper.get('[data-testid=interaction-panel-node]');
    expect(header.findComponent(HashLink).props('text')).toBe(TARGET);
    const listed = wrapper.getComponent(AddressInteractionConnectionList).findAllComponents(HashLink).map(link => link.props('text'));
    expect(listed).toEqual([SOURCE, OTHER]);

    await wrapper.get('[data-testid=interaction-panel-clear-node]').trigger('click');
    expect(wrapper.find('[data-testid=interaction-panel-node]').exists()).toBe(false);
    expect(wrapper.getComponent(AddressInteractionConnectionList).findAllComponents(HashLink)).toHaveLength(4);
  });

  it('should go back from a connection to the selected address', async () => {
    const wrapper = createWrapper([interaction(), interaction('eth', '0xother', TARGET, OTHER)]);
    const targetNode = wrapper.findAll('[data-testid=interaction-node]').find(node =>
      node.attributes('aria-label')?.includes(TARGET),
    );
    assert(targetNode);
    await targetNode.trigger('click');
    await wrapper.findAll('[data-testid=interaction-connection]')[0].trigger('click');
    expect(wrapper.find('[data-testid=interaction-connection-list]').exists()).toBe(false);

    await wrapper.get('[data-testid=interaction-details-back]').trigger('click');

    expect(wrapper.find('[data-testid=interaction-details]').exists()).toBe(false);
    expect(wrapper.get('[data-testid=interaction-panel-node]').findComponent(HashLink).props('text')).toBe(TARGET);
  });

  it('should open history events filtered to the connection or a single transaction', async () => {
    const push = vi.fn<Router['push']>().mockResolvedValue(undefined);
    vi.mocked(useRouter).mockReturnValueOnce(createMock<Router>({ push }));
    const wrapper = createWrapper([interaction(), interaction('eth', '0xsecond-transaction')]);
    await wrapper.get('[data-testid=interaction-connection]').trigger('click');

    await wrapper.get('[data-testid=interaction-history-link]').trigger('click');
    expect(push).toHaveBeenLastCalledWith({
      name: '/history/events/',
      query: { location: 'ethereum', txRefs: ['0xeth-transaction', '0xsecond-transaction'] },
    });

    await wrapper.findAll('[data-testid=interaction-tx-history]')[1].trigger('click');
    expect(push).toHaveBeenLastCalledWith({ name: '/history/events/', query: { location: 'ethereum', txRefs: ['0xsecond-transaction'] } });
  });

  it('should focus a suggested address, combine it with chain filters and let users reset an empty result', async () => {
    getAddressName.mockImplementation(address => address === OTHER ? 'Savings' : undefined);
    const wrapper = createWrapper([
      interaction(),
      interaction('optimism'),
      interaction('eth', '0xother', TARGET, OTHER),
    ]);

    await searchAddress(wrapper, OTHER);
    expect(wrapper.findAll('[data-testid=interaction-edge]')).toHaveLength(1);
    expect(wrapper.get('[data-testid=interaction-panel-node]').findComponent(HashLink).props('text')).toBe(OTHER);

    await wrapper.get('[data-testid=interaction-chain][data-chain=optimism]').trigger('click');
    expect(wrapper.find('[data-testid=interaction-no-results]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid=interaction-connection]')).toHaveLength(0);

    await wrapper.get('[data-testid=interaction-reset-filters]').trigger('click');
    expect(wrapper.findAll('[data-testid=interaction-edge]')).toHaveLength(3);
    expect(wrapper.getComponent(LocationLabelSelector).props('modelValue')).toBe('');
    expect(wrapper.find('[data-testid=interaction-no-results]').exists()).toBe(false);
  });

  it('should clear transaction details when a chain filter hides the selected connection', async () => {
    const wrapper = createWrapper([interaction(), interaction('optimism')]);
    await wrapper.findAll('[data-testid=interaction-connection]')[0].trigger('click');
    expect(transactionLinks(wrapper).map(link => link.props('location'))).toEqual(['eth']);

    await wrapper.get('[data-testid=interaction-chain][data-chain=optimism]').trigger('click');
    expect(transactionLinks(wrapper)).toHaveLength(0);
    expect(wrapper.findAll('[data-testid=interaction-edge]')).toHaveLength(1);
    await wrapper.get('[data-testid=interaction-connection]').trigger('click');
    expect(transactionLinks(wrapper).map(link => link.props('location'))).toEqual(['optimism']);
  });

  it('should lay out nodes and connections deterministically regardless of history order', () => {
    const interactions = [interaction(), interaction('optimism'), interaction('eth', '0xother', TARGET, OTHER)];
    expect(createAddressInteractionGraph(interactions)).toEqual(createAddressInteractionGraph([...interactions].reverse()));
  });
});

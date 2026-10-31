import type { ECElementEvent, EChartsOption } from 'echarts';
import type { InteractionGraph } from './address-interaction-graph';
import type { AddressInteraction } from './address-interaction-types';
import type { InteractionFilters } from './interaction-scene';
import { ClickButtonStub, graphOf, graphSeries, interaction, OTHER, sceneOf, SOURCE, TARGET } from '@test/utils/address-interactions';
import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import AddressInteractionCanvas from './AddressInteractionCanvas.vue';

const { getAddressName, getEnsName, chartMounts, scrambleData } = await vi.hoisted(async () => {
  const { ref } = await import('vue');
  return {
    chartMounts: vi.fn<() => void>(),
    getAddressName: vi.fn<(address: string, chain?: string) => string | undefined>(),
    getEnsName: vi.fn<(address: string) => string | null>(() => null),
    scrambleData: ref<boolean>(false),
  };
});

vi.mock('vue-echarts', () => ({
  default: {
    emits: ['click'],
    mounted: chartMounts,
    name: 'VChart',
    props: ['option'],
    template: '<div data-testid="address-interaction-network" />',
  },
}));

vi.mock('./use-node-avatars', () => ({
  useNodeAvatars: (): object => ref(new Map()),
}));

vi.mock('@/modules/statistics/use-graph', () => ({
  useGraph: (): object => ({ baseColor: ref('#7e4a3b'), secondaryColor: ref('#3f3f46') }),
}));

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName, getEnsName }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getChainName: (chain: string): string => chain === 'eth' ? 'Ethereum' : 'Optimism',
  }),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): object => ({
    scrambleAddress: (address: string): string => get(scrambleData) ? 'hidden-address' : address,
    scrambleData,
  }),
}));

const interactions: AddressInteraction[] = [
  interaction('eth', '0xa'),
  interaction('optimism', '0xb'),
  interaction('eth', '0xc', TARGET, OTHER),
];

function props(graph: InteractionGraph, filters: Partial<InteractionFilters> = {}): InstanceType<typeof AddressInteractionCanvas>['$props'] {
  return {
    chain: filters.chain,
    chains: ['eth', 'optimism'],
    graph,
    scene: sceneOf(graph, filters),
    selection: { connectionIds: new Set(), nodeIds: new Set() },
  };
}

function createWrapper(graph: InteractionGraph = graphOf(interactions)): VueWrapper<InstanceType<typeof AddressInteractionCanvas>> {
  return mount(AddressInteractionCanvas, {
    global: {
      stubs: {
        RuiButton: ClickButtonStub,
      },
    },
    props: props(graph),
  });
}

function nodeLabels(wrapper: VueWrapper<InstanceType<typeof AddressInteractionCanvas>>): string[] {
  const formatter = graphSeries(wrapper).label?.formatter;
  assert(typeof formatter === 'function');
  return wrapper.props('scene').nodes.map((_node, dataIndex) =>
    formatter(createMock<Parameters<typeof formatter>[0]>({ dataIndex, dataType: 'node' })));
}

function tooltips(wrapper: VueWrapper): string[] {
  const option: EChartsOption = wrapper.getComponent({ name: 'VChart' }).props('option');
  const tooltip = [option.tooltip].flat()[0];
  assert(tooltip && typeof tooltip.formatter === 'function');
  const { formatter } = tooltip;
  return [
    formatter(createMock<Parameters<typeof formatter>[0]>({ dataIndex: 0, dataType: 'node' }), ''),
    formatter(createMock<Parameters<typeof formatter>[0]>({ dataIndex: 0, dataType: 'edge' }), ''),
  ].map(String);
}

function click(wrapper: VueWrapper, dataType: 'node' | 'edge', dataIndex: number): void {
  wrapper.getComponent({ name: 'VChart' }).vm.$emit('click', createMock<ECElementEvent>({ dataIndex, dataType }));
}

describe('address interaction canvas', () => {
  beforeEach(() => {
    set(scrambleData, false);
    getAddressName.mockReset();
    getEnsName.mockReset();
    getEnsName.mockReturnValue(null);
    chartMounts.mockClear();
  });

  it('should emit the scene objects behind node and edge clicks', () => {
    const wrapper = createWrapper();
    const { connections, nodes } = wrapper.props('scene');

    click(wrapper, 'node', 1);
    click(wrapper, 'edge', 0);
    click(wrapper, 'node', 5);

    expect(wrapper.emitted('select-node')).toEqual([[nodes[1]]]);
    expect(wrapper.emitted('select-connection')).toEqual([[connections[0]]]);
  });

  it('should colour a pair by its only chain, a pair on several chains neutrally, and with a chain picked only the pairs active on it', async () => {
    const wrapper = createWrapper();
    const colour = (): unknown[] => graphSeries(wrapper).links?.map(link => link.lineStyle?.color) ?? [];

    expect(colour()).toEqual(['#8e8e93', '#2a78d6']);

    await wrapper.setProps(props(wrapper.props('graph'), { chain: 'optimism' }));

    expect(colour()).toEqual(['#eb6834', '#8e8e93']);
  });

  it('should keep pan and zoom while filters and selection change, and reset them for a new graph or on fit', async () => {
    const wrapper = createWrapper();
    expect(chartMounts).toHaveBeenCalledTimes(1);

    await wrapper.setProps({
      ...props(wrapper.props('graph'), { minTransactions: 2 }),
      selection: { connectionIds: new Set(), nodeIds: new Set([SOURCE]) },
    });
    expect(chartMounts).toHaveBeenCalledTimes(1);

    await wrapper.get('[data-testid=interaction-fit-graph]').trigger('click');
    expect(chartMounts).toHaveBeenCalledTimes(2);

    await wrapper.setProps(props(graphOf([interaction('optimism', '0xnew')])));
    expect(chartMounts).toHaveBeenCalledTimes(3);
  });

  it('should break a pair\'s tooltip down by chain', () => {
    expect(tooltips(createWrapper())[1]).toBe([
      `${SOURCE} ↔ ${TARGET}`,
      'address_interactions.connection_summary::Ethereum, 1',
      'address_interactions.connection_summary::Optimism, 1',
    ].join('\n'));
  });

  it('should show an ENS name for an address seen only on a chain without a name for it', () => {
    const ensOnly = '0x4444444444444444444444444444444444444444';
    getEnsName.mockImplementation(address => address === ensOnly ? 'vitalik.eth' : null);
    const wrapper = createWrapper(graphOf([interaction('optimism', '0xop', SOURCE, ensOnly)]));

    expect(nodeLabels(wrapper)).toEqual(['0x111111...111111', 'vitalik.eth']);
  });

  it('should end a long name in an ellipsis rather than widening its label', () => {
    getAddressName.mockReturnValue('A rather long address book name');
    const wrapper = createWrapper();

    expect(nodeLabels(wrapper)[0]).toBe('A rather long addre…');
    expect(graphSeries(wrapper).label?.width).toBeUndefined();
  });

  it('should resolve address names but remove names and raw addresses from labels and tooltips when scrambling', async () => {
    getAddressName.mockReturnValue('Treasury wallet');
    const wrapper = createWrapper();

    expect(nodeLabels(wrapper)).toEqual(['Treasury wallet', 'Treasury wallet', 'Treasury wallet']);
    expect(tooltips(wrapper)[0]).toBe('Treasury wallet\nEthereum, Optimism');

    set(scrambleData, true);
    await nextTick();

    const visible = [...nodeLabels(wrapper), ...tooltips(wrapper)].join(' ');
    expect(visible).not.toContain('Treasury wallet');
    expect(visible).not.toContain(SOURCE);
    expect(visible).not.toContain(TARGET);
    expect(tooltips(wrapper)[0]).toContain('hidden-address');
  });
});

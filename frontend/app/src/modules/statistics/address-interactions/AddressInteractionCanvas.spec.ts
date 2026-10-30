import { createMock } from '@test/utils/create-mock';
import { mount, type VueWrapper } from '@vue/test-utils';
import { useResizeObserver } from '@vueuse/core';
import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { createAddressInteractionGraph, type InteractionGraph } from './address-interaction-graph';
import AddressInteractionCanvas from './AddressInteractionCanvas.vue';

const { getAddressName } = vi.hoisted(() => ({
  getAddressName: vi.fn<() => string | undefined>(),
}));
const scrambleData = ref(false);

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({
    getChainName: (chain: string): string => chain === 'eth' ? 'Ethereum' : 'Optimism',
  }),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: (): object => ({
    scrambleAddress: (address: string): string => scrambleData.value ? 'hidden-address' : address,
    scrambleData,
  }),
}));

const SOURCE = '0x1111111111111111111111111111111111111111';
const TARGET = '0x2222222222222222222222222222222222222222';

function createWrapper(graph: InteractionGraph = createAddressInteractionGraph([{ chain: 'eth', source: SOURCE, target: TARGET, txHash: '0xtransaction' }])): VueWrapper<InstanceType<typeof AddressInteractionCanvas>> {
  return mount(AddressInteractionCanvas, {
    global: {
      stubs: {
        RuiButton: { emits: ['click'], template: '<button type="button" v-bind="$attrs" @click="$emit(\'click\')"><slot /></button>' },
        RuiIcon: true,
      },
    },
    props: { graph },
  });
}

function parseTransform(value: string | undefined): number[] {
  assert(value);
  const numbers = value.match(/-?[\d.]+/g);
  assert(numbers);
  return numbers.map(Number);
}

async function resizeViewport(width: number, height: number): Promise<void> {
  const callback = vi.mocked(useResizeObserver).mock.lastCall?.[1];
  assert(callback);
  callback([createMock<ResizeObserverEntry>({ contentRect: new DOMRect(0, 0, width, height) })], new ResizeObserver(vi.fn()));
  await nextTick();
}

describe('address interaction canvas', () => {
  beforeEach(() => {
    scrambleData.value = false;
    getAddressName.mockReset();
    vi.mocked(useResizeObserver).mockClear();
  });

  it.each([
    { deltaMode: 0, deltaY: -60 },
    { deltaMode: 2, deltaY: -0.1 },
  ])('should anchor wheel zoom and restore the fitted view for delta mode $deltaMode', async ({ deltaMode, deltaY }) => {
    const wrapper = createWrapper();
    await resizeViewport(960, 600);
    const viewport = wrapper.get<HTMLElement>('[data-testid=interaction-canvas-viewport]');
    vi.spyOn(viewport.element, 'getBoundingClientRect').mockReturnValue(new DOMRect(40, 70, 960, 600));
    const content = wrapper.get('[data-testid=interaction-canvas-transform]');
    const initial = content.attributes('transform');
    const before = parseTransform(initial);

    await viewport.trigger('wheel', { deltaMode, deltaY, clientX: 220, clientY: 190 });

    const after = parseTransform(content.attributes('transform'));
    expect(after[2]).toBeCloseTo(before[2] * Math.exp(60 * 0.002));
    expect((180 - after[0]) / after[2]).toBeCloseTo((180 - before[0]) / before[2]);
    expect((120 - after[1]) / after[2]).toBeCloseTo((120 - before[1]) / before[2]);
    await wrapper.get('[data-testid=interaction-fit-graph]').trigger('click');
    expect(content.attributes('transform')).toBe(initial);
  });

  it('should allow zooming out from the fitted view and keep button zoom centered', async () => {
    const wrapper = createWrapper();
    await resizeViewport(960, 640);
    const content = wrapper.get('[data-testid=interaction-canvas-transform]');
    const before = parseTransform(content.attributes('transform'));
    await wrapper.get('[data-testid=interaction-zoom-out]').trigger('click');
    const after = parseTransform(content.attributes('transform'));
    expect(after[2]).toBeLessThan(before[2]);
    expect((480 - after[0]) / after[2]).toBeCloseTo((480 - before[0]) / before[2]);
    expect((320 - after[1]) / after[2]).toBeCloseTo((320 - before[1]) / before[2]);
  });

  it('should enlarge and center small graphs within the measured surface', async () => {
    const wrapper = createWrapper();

    await resizeViewport(960, 640);

    expect(parseTransform(wrapper.get('[data-testid=interaction-canvas-transform]').attributes('transform'))).toEqual([165, 200, 1.5]);
  });

  it('should fit both measured dimensions and reset pan and zoom on height-only resize', async () => {
    const graph = createAddressInteractionGraph([{ chain: 'eth', source: SOURCE, target: TARGET, txHash: '0xtransaction' }]);
    graph.nodes[1].y = 750;
    const wrapper = createWrapper(graph);
    const network = wrapper.get('[data-testid=address-interaction-network]');
    const content = wrapper.get('[data-testid=interaction-canvas-transform]');

    await resizeViewport(960, 600);

    expect(network.attributes('viewBox')).toBe('0 0 960 600');
    const fitted = parseTransform(content.attributes('transform'));
    expect(fitted[2]).toBeCloseTo(600 / 840);
    expect(fitted[0]).toBeCloseTo((960 - 420 * fitted[2]) / 2);
    expect(fitted[1]).toBe(0);

    await wrapper.get('[data-testid=interaction-zoom-in]').trigger('click');
    await wrapper.get('[data-testid=interaction-canvas-viewport]').trigger('keydown', { key: 'ArrowDown' });
    await resizeViewport(960, 840);

    expect(network.attributes('viewBox')).toBe('0 0 960 840');
    expect(parseTransform(content.attributes('transform'))).toEqual([270, 0, 1]);
  });

  it('should reset pan and zoom when filters replace the graph', async () => {
    const wrapper = createWrapper();
    const viewport = wrapper.get('[data-testid=interaction-canvas-viewport]');
    const content = wrapper.get('[data-testid=interaction-canvas-transform]');
    const initial = content.attributes('transform');
    await wrapper.get('[data-testid=interaction-zoom-in]').trigger('click');
    await viewport.trigger('keydown', { key: 'ArrowRight' });
    expect(content.attributes('transform')).not.toBe(initial);

    await wrapper.setProps({
      graph: createAddressInteractionGraph([{ chain: 'optimism', source: SOURCE, target: TARGET, txHash: '0xfiltered' }]),
    });

    expect(content.attributes('transform')).toBe(initial);
    expect(wrapper.get('[data-testid=interaction-node]').attributes('aria-label')).toContain('Optimism');
  });

  it('should emit the original graph objects for Enter and Space and expose controlled selection', async () => {
    const wrapper = createWrapper();
    const graph = wrapper.props('graph');
    const node = wrapper.get('[data-testid=interaction-node]');
    const edge = wrapper.get('[data-testid=interaction-edge]');

    expect(node.attributes('aria-label')).toContain('Ethereum');
    expect(node.attributes('tabindex')).toBe('0');
    expect(edge.attributes('tabindex')).toBe('0');

    await node.trigger('keydown', { key: 'Enter' });
    await node.trigger('keydown', { key: ' ' });
    await edge.trigger('keydown', { key: 'Enter' });
    await edge.trigger('keydown', { key: ' ' });

    expect(wrapper.emitted('select-node')).toEqual([[graph.nodes[0]], [graph.nodes[0]]]);
    expect(wrapper.emitted('select-connection')).toEqual([[graph.connections[0]], [graph.connections[0]]]);
    expect(node.attributes('aria-pressed')).toBe('false');

    await wrapper.setProps({ selectedConnectionId: graph.connections[0].id, selectedNodeId: graph.nodes[0].id });

    expect(node.attributes('aria-pressed')).toBe('true');
    expect(edge.attributes('aria-pressed')).toBe('true');
  });

  it('should resolve address labels but remove names and raw addresses from labels and tooltips when scrambling', async () => {
    getAddressName.mockReturnValue('Treasury wallet');
    const wrapper = createWrapper();
    const network = wrapper.get('[data-testid=address-interaction-network]');

    expect(network.text()).toContain('Treasury wallet');
    expect(wrapper.get('[data-testid=interaction-node]').attributes('aria-label')).toContain('Treasury wallet');

    scrambleData.value = true;
    await nextTick();

    expect(network.html()).not.toContain('Treasury wallet');
    expect(network.html()).not.toContain(SOURCE);
    expect(network.html()).not.toContain(TARGET);
    expect(wrapper.get('[data-testid=interaction-node]').attributes('aria-label')).toContain('hidden-address');
    expect(wrapper.get('[data-testid=interaction-edge]').attributes('aria-label')).toContain('hidden-address');
  });
});

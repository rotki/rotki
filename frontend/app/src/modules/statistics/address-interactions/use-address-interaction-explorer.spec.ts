import type { AddressInteraction } from './address-interaction-types';
import { links } from '@test/utils/address-interactions';
import { assert, describe, expect, it, vi } from 'vitest';
import { nextTick, ref } from 'vue';
import { createAddressInteractionGraph } from './address-interaction-graph';
import { useAddressInteractionExplorer } from './use-address-interaction-explorer';

vi.mock('./address-interaction-graph', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./address-interaction-graph')>();
  return { ...actual, createAddressInteractionGraph: vi.fn(actual.createAddressInteractionGraph) };
});

vi.mock('@/modules/accounts/address-book/use-address-name-resolution', () => ({
  useAddressNameResolution: (): object => ({ getAddressName: (): undefined => undefined, getEnsName: (): null => null }),
}));

vi.mock('@/modules/core/common/use-supported-chains', () => ({
  useSupportedChains: (): object => ({ getChainName: (chain: string): string => chain }),
}));

vi.mock('@/modules/settings/use-scramble', async () => {
  const { ref } = await import('vue');
  return { useScramble: (): object => ({ scrambleAddress: (address: string): string => address, scrambleData: ref<boolean>(false) }) };
});

describe('address interaction explorer', () => {
  it('should show the address selected on the graph in the search box, and select whatever is searched', () => {
    const explorer = useAddressInteractionExplorer(links(['a', 'b'], ['b', 'c']));
    const [a, b] = get(explorer.scene).nodes;

    set(explorer.modelAddress, 'a');
    explorer.selectNode(b);
    expect(get(explorer.modelAddress)).toBe('b');

    set(explorer.modelAddress, 'a');
    expect(get(explorer.selectedNode)).toBe(a);

    set(explorer.modelAddress, '');
    expect(get(explorer.selectedNode)).toBeUndefined();
  });

  it('should lower the minimum when refreshed data has no pair that busy', async () => {
    const source = ref<AddressInteraction[]>(links(['a', 'b', 6]));
    const explorer = useAddressInteractionExplorer(source);
    set(explorer.modelMinTransactions, 5);

    set(source, links(['a', 'b', 2]));
    await nextTick();

    expect(get(explorer.modelMinTransactions)).toBe(2);
    expect(get(explorer.stats).connections).toBe(1);
  });

  it('should keep focus on the same cluster when refreshed clusters re-sort', async () => {
    const source = ref<AddressInteraction[]>(links(['a', 'b'], ['b', 'c'], ['x', 'y']));
    const explorer = useAddressInteractionExplorer(source);
    explorer.selectCluster(1);
    expect(get(explorer.focus)?.nodeIds).toEqual(new Set(['x', 'y']));

    set(source, links(['a', 'b'], ['x', 'y'], ['y', 'z'], ['z', 'w']));
    await nextTick();

    expect(get(explorer.selectedClusterIndex)).toBe(0);
    expect(get(explorer.focus)?.nodeIds).toEqual(new Set(['w', 'x', 'y', 'z']));
  });

  it('should list only the focused cluster\'s connections', () => {
    const explorer = useAddressInteractionExplorer(links(['a', 'b'], ['b', 'c'], ['x', 'y']));

    explorer.selectCluster(1);

    expect(get(explorer.connections).map(({ id }) => id)).toEqual([JSON.stringify(['x', 'y'])]);
  });

  it('should skip rebuilding the graph when a refresh returns the same rows, and keep it when only their order changes', async () => {
    const source = ref<AddressInteraction[]>(links(['a', 'b'], ['b', 'c']));
    const explorer = useAddressInteractionExplorer(source);
    const before = get(explorer.graph);
    const builds = vi.mocked(createAddressInteractionGraph).mock.calls.length;

    set(source, links(['a', 'b'], ['b', 'c']));
    await nextTick();
    expect(get(explorer.graph)).toBe(before);
    expect(vi.mocked(createAddressInteractionGraph).mock.calls).toHaveLength(builds);

    set(source, [...links(['b', 'c']), ...links(['a', 'b'])]);
    await nextTick();
    expect(get(explorer.graph)).toBe(before);
    expect(vi.mocked(createAddressInteractionGraph).mock.calls).toHaveLength(builds + 1);
  });

  it('should draw both ends of a selected pair as selected', () => {
    const explorer = useAddressInteractionExplorer(links(['a', 'b'], ['b', 'c']));
    const [pair] = get(explorer.scene).connections;

    explorer.selectConnection(pair);

    expect(get(explorer.selection).nodeIds).toEqual(new Set(['a', 'b']));
  });

  it('should not select a connection the filters grey out', () => {
    const explorer = useAddressInteractionExplorer(links(['a', 'b', 2], ['b', 'c']));
    set(explorer.modelMinTransactions, 2);
    const [, greyed] = get(explorer.scene).connections;

    explorer.selectConnection(greyed);

    expect(get(explorer.selectedConnection)).toBeUndefined();
  });

  it('should drop a path whose far end disappears on refresh', async () => {
    const source = ref<AddressInteraction[]>(links(['a', 'b'], ['b', 'c']));
    const explorer = useAddressInteractionExplorer(source);
    const [a, , c] = get(explorer.scene).nodes;
    explorer.selectNode(a);
    explorer.startPath();
    explorer.selectNode(c);
    assert(get(explorer.path));

    set(source, links(['a', 'b']));
    await nextTick();

    expect(get(explorer.pathTarget)).toBeUndefined();
    expect(get(explorer.focus)?.nodeIds).toEqual(new Set(['a', 'b']));
  });

  it('should keep picking a path target when the origin is clicked again', () => {
    const explorer = useAddressInteractionExplorer(links(['a', 'b'], ['b', 'c']));
    const [a, , c] = get(explorer.scene).nodes;
    explorer.selectNode(a);
    explorer.startPath();

    explorer.selectNode(a);
    expect(get(explorer.pickingPath)).toBe(true);
    expect(get(explorer.selectedNode)).toBe(a);

    explorer.selectNode(c);
    const path = get(explorer.path);
    assert(path);
    expect(path.nodes.map(({ id }) => id)).toEqual(['a', 'b', 'c']);
  });
});

import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationTreeExpansion } from '@/modules/locations/use-location-tree-expansion';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

const tree = [
  node('total', null, 'Total'),
  node('banks', 'total', 'Banks'),
  node('custom:ing', 'banks', 'ING', { isBuiltin: false }),
  node('blockchain', 'total', 'Blockchains'),
  node('evm chains', 'blockchain', 'EVM Chains'),
  node('ethereum', 'evm chains', 'Ethereum'),
];

describe('useLocationTreeExpansion', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should open the branches holding a custom location and fold the rest', () => {
    useLocationTreeStore().setNodes(tree);
    const { isExpanded } = useLocationTreeExpansion();
    expect(isExpanded('banks')).toBe(true);
    expect(isExpanded('blockchain')).toBe(false);
    expect(isExpanded('evm chains')).toBe(false);
  });

  it('should take the starting point from a tree that loads after mounting', async () => {
    const { isExpanded } = useLocationTreeExpansion();
    useLocationTreeStore().setNodes(tree);
    await nextTick();
    expect(isExpanded('banks')).toBe(true);
  });

  it('should not fold or unfold on its own when the tree changes later', async () => {
    const store = useLocationTreeStore();
    store.setNodes(tree);
    const { isExpanded } = useLocationTreeExpansion();

    store.setNodes([...tree.filter(item => item.identifier !== 'custom:ing'), node('custom:cold', 'ethereum', 'Cold wallet', { isBuiltin: false })]);
    await nextTick();

    expect(isExpanded('banks')).toBe(true);
    expect(isExpanded('blockchain')).toBe(false);
  });

  it('should open the way to a revealed location and flip a toggled one', () => {
    const store = useLocationTreeStore();
    store.setNodes([...tree, node('custom:cold', 'ethereum', 'Cold wallet', { isBuiltin: false })]);
    const { isExpanded, reveal, toggle } = useLocationTreeExpansion();
    toggle('blockchain');
    expect(isExpanded('blockchain')).toBe(false);

    reveal('custom:cold');
    expect(['blockchain', 'evm chains', 'ethereum'].map(isExpanded)).toEqual([true, true, true]);
    expect(isExpanded('custom:cold')).toBe(false);
  });
});

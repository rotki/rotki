import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

describe('useLocationTreeStore', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('banks', 'total', 'Banks'),
      node('custom:ing', 'banks', 'ING', { isBuiltin: false }),
      node('custom:savings', 'custom:ing', 'Savings', { isBuiltin: false }),
      node('custom:closed', 'banks', 'Closed', { isActive: false, isBuiltin: false }),
      node('qonto', 'banks', 'Qonto'),
    ]);
  });

  it('should give the path below the total', () => {
    const store = useLocationTreeStore();
    expect(store.pathOf('custom:savings').map(x => x.name)).toEqual(['Banks', 'ING', 'Savings']);
    expect(store.pathOf('total')).toEqual([]);
    expect(store.pathOf('unknown')).toEqual([]);
  });

  it('should give the path label, the sorted children and the subtree of a location', () => {
    const store = useLocationTreeStore();
    expect(store.pathLabelOf('custom:savings')).toBe('Banks › ING › Savings');
    expect(store.pathLabelOf('unknown')).toBe('unknown');
    expect(store.childrenOf('banks').map(x => x.name)).toEqual(['Closed', 'ING', 'Qonto']);
    expect([...store.subtreeOf('banks')].sort()).toEqual(['banks', 'custom:closed', 'custom:ing', 'custom:savings', 'qonto']);
  });

  it('should order locations after their ancestors and siblings by name, not by identifier', () => {
    const store = useLocationTreeStore();
    store.setNodes([...store.nodes, node('abn', 'banks', 'ABN')]);

    expect(store.sortByTree(['qonto', 'custom:savings', 'abn', 'banks', 'custom:ing', 'custom:closed']))
      .toEqual(['banks', 'abn', 'custom:closed', 'custom:ing', 'custom:savings', 'qonto']);
  });

  it('should keep a location\'s children right after it when a sibling\'s name starts with its name', () => {
    const store = useLocationTreeStore();
    store.setNodes([...store.nodes, node('custom:ings', 'banks', 'INGS', { isBuiltin: false })]);

    expect(store.sortByTree(['custom:ings', 'custom:savings', 'custom:ing']))
      .toEqual(['custom:ing', 'custom:savings', 'custom:ings']);
  });

  it('should put locations missing from the tree last', () => {
    expect(useLocationTreeStore().sortByTree(['nowhere', 'qonto', 'banks'])).toEqual(['banks', 'qonto', 'nowhere']);
  });

  it('should give a path only for a location whose name another location shares', () => {
    const store = useLocationTreeStore();
    store.setNodes([...store.nodes, node('exchanges', 'total', 'Exchanges'), node('custom:ing-x', 'exchanges', 'ing', { isBuiltin: false })]);
    expect(store.pathIfNameShared('custom:ing')).toBe('Banks › ING');
    expect(store.pathIfNameShared('custom:ing-x')).toBe('Exchanges › ing');
    expect(store.pathIfNameShared('qonto')).toBeUndefined();
    expect(store.pathIfNameShared('unknown')).toBeUndefined();
  });

  it('should offer every active location but the categories for new data', () => {
    expect([...useLocationTreeStore().assignableIdentifiers ?? []]).toEqual(['custom:ing', 'custom:savings', 'qonto']);
  });

  it('should keep a built-in location assignable while only custom locations sit below it', () => {
    const store = useLocationTreeStore();
    store.setNodes([
      node('total', null, 'Total'),
      node('other', 'total', 'Other'),
      node('external', 'other', 'External'),
      node('custom:cold', 'external', 'Cold storage', { isBuiltin: false }),
    ]);
    expect([...store.assignableIdentifiers ?? []]).toEqual(['external', 'custom:cold']);
  });
});

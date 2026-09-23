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

  it('should give the path below the total, sorted children and the subtree', () => {
    const store = useLocationTreeStore();
    expect(store.pathOf('custom:savings').map(x => x.name)).toEqual(['Banks', 'ING', 'Savings']);
    expect(store.pathOf('total')).toEqual([]);
    expect(store.pathOf('unknown')).toEqual([]);
    expect(store.pathLabelOf('custom:savings')).toBe('Banks › ING › Savings');
    expect(store.pathLabelOf('unknown')).toBe('unknown');
    expect(store.childrenOf('banks').map(x => x.name)).toEqual(['Closed', 'ING', 'Qonto']);
    expect([...store.subtreeOf('banks')].sort()).toEqual(['banks', 'custom:closed', 'custom:ing', 'custom:savings', 'qonto']);
  });

  it('should name a location by its path only when another location shares its name', () => {
    const store = useLocationTreeStore();
    store.setNodes([...store.nodes, node('exchanges', 'total', 'Exchanges'), node('custom:ing-x', 'exchanges', 'ing', { isBuiltin: false })]);
    expect(store.distinctNameOf('qonto')).toBe('Qonto');
    expect(store.distinctNameOf('custom:ing')).toBe('Banks › ING');
    expect(store.distinctNameOf('custom:ing-x')).toBe('Exchanges › ing');
    expect(store.distinctNameOf('unknown')).toBeUndefined();
  });

  it('should order locations after their ancestors, siblings by name', () => {
    expect(useLocationTreeStore().sortByTree(['qonto', 'custom:savings', 'banks', 'custom:ing'])).toEqual(['banks', 'custom:ing', 'custom:savings', 'qonto']);
  });

  it('should offer every active location but the categories for new data', () => {
    expect(useLocationTreeStore().assignableNodes.map(x => x.identifier)).toEqual(['custom:ing', 'custom:savings', 'qonto']);
  });

  it('should keep a built-in location assignable while only custom locations sit below it', () => {
    const store = useLocationTreeStore();
    store.setNodes([
      node('total', null, 'Total'),
      node('other', 'total', 'Other'),
      node('external', 'other', 'External'),
      node('custom:cold', 'external', 'Cold storage', { isBuiltin: false }),
    ]);
    expect(store.assignableNodes.map(x => x.identifier)).toEqual(['external', 'custom:cold']);
  });
});

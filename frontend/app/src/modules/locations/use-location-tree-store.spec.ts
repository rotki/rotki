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
    expect(store.childrenOf('banks').map(x => x.name)).toEqual(['Closed', 'ING', 'Qonto']);
    expect([...store.subtreeOf('banks')].sort()).toEqual(['banks', 'custom:closed', 'custom:ing', 'custom:savings', 'qonto']);
  });

  it('should offer every active location but the total for new data', () => {
    expect(useLocationTreeStore().assignableNodes.map(x => x.identifier)).toEqual(['banks', 'custom:ing', 'custom:savings', 'qonto']);
  });
});

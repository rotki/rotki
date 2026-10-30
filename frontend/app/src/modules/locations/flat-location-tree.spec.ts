import { createCustomPinia } from '@test/utils/create-pinia';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { flatLocationTree } from '@/modules/locations/flat-location-tree';
import { ROOT_LOCATION, useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

describe('flatLocationTree', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  const locations = { banks: {}, blockchain: {}, kraken: { label: 'Kraken' } };

  it('should place every location directly below the total', () => {
    const nodes = flatLocationTree(locations);

    expect(nodes.find(node => node.identifier === ROOT_LOCATION)?.parentIdentifier).toBeNull();
    expect(nodes.filter(node => node.identifier !== ROOT_LOCATION).map(node => [node.identifier, node.parentIdentifier]))
      .toEqual([['banks', ROOT_LOCATION], ['blockchain', ROOT_LOCATION], ['kraken', ROOT_LOCATION]]);
  });

  it('should keep a single total when the details already name one', () => {
    const nodes = flatLocationTree({ ...locations, [ROOT_LOCATION]: { label: 'Total' } });

    expect(nodes.filter(node => node.identifier === ROOT_LOCATION)).toHaveLength(1);
  });

  it('should keep every location assignable, with no path and no shared name', () => {
    const store = useLocationTreeStore();
    store.setNodes(flatLocationTree(locations));

    expect([...store.assignableIdentifiers ?? []]).toEqual(['banks', 'blockchain', 'kraken']);
    expect(store.pathOf('kraken').map(node => node.identifier)).toEqual(['kraken']);
    expect(store.pathIfNameShared('banks')).toBeUndefined();
  });
});

import { createCustomPinia } from '@test/utils/create-pinia';
import { createLocationNode as node } from '@test/utils/location-tree';
import { setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it } from 'vitest';
import { useLocationStore } from '@/modules/core/common/use-location-store';
import { DEFAULT_LOCATION_ICON } from '@/modules/locations/location-icons';
import { useLocationTreeStore } from '@/modules/locations/use-location-tree-store';

describe('useLocationStore', () => {
  beforeEach(() => {
    setActivePinia(createCustomPinia());
  });

  it('should append the custom locations of the tree to the built-in ones, not the built-in tree nodes', () => {
    const store = useLocationStore();
    store.allLocations = { kraken: { image: 'kraken.svg', isExchange: true, label: 'Kraken' } };
    useLocationTreeStore().setNodes([
      node('total', null, 'Total'),
      node('kraken', 'total', 'Kraken'),
      node('custom:desk', 'total', 'Desk', { icon: 'lu-landmark', isBuiltin: false }),
      node('custom:odd', 'total', 'Odd', { icon: 'not-an-icon', isBuiltin: false }),
      node('custom:logo', 'total', 'Logo', { image: 'logo.png', isBuiltin: false }),
    ]);

    const byIdentifier = new Map(store.tradeLocations.map(item => [item.identifier, item]));

    expect([...byIdentifier.keys()]).toEqual(['kraken', 'custom:desk', 'custom:odd', 'custom:logo']);
    expect(byIdentifier.get('custom:desk')).toEqual({ icon: 'lu-landmark', identifier: 'custom:desk', image: null, name: 'Desk' });
    expect(byIdentifier.get('custom:odd')?.icon).toBe(DEFAULT_LOCATION_ICON);
    expect(byIdentifier.get('custom:logo')?.image).toContain('custom%3Alogo/image');
  });

  it('should keep the built-in entries when only the tree changes', () => {
    const store = useLocationStore();
    store.allLocations = { kraken: { isExchange: true, label: 'Kraken' } };
    useLocationTreeStore().setNodes([node('custom:desk', 'total', 'Desk', { isBuiltin: false })]);
    const [kraken] = store.tradeLocations;

    useLocationTreeStore().setNodes([node('custom:desk', 'total', 'Office', { isBuiltin: false })]);

    expect(store.tradeLocations[0]).toBe(kraken);
    expect(store.tradeLocations[1]?.name).toBe('Office');
  });
});

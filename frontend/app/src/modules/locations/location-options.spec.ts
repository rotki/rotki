import type { TradeLocationData } from '@/modules/core/common/location';
import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { createLocationNode as node } from '@test/utils/location-tree';
import { describe, expect, it } from 'vitest';
import { locationOptions, type LocationOptionsInput } from '@/modules/locations/location-options';

const tree: Record<string, LocationNode[]> = {
  'custom:closed': [node('banks', 'total', 'Banks'), node('custom:closed', 'banks', 'Closed')],
  'custom:ing': [node('banks', 'total', 'Banks'), node('custom:ing', 'banks', 'ING')],
  'kraken': [node('exchanges', 'total', 'Exchanges'), node('kraken', 'exchanges', 'Kraken')],
  'total': [],
};

const locations: TradeLocationData[] = [
  { identifier: 'total', name: 'Total' },
  { identifier: 'kraken', name: 'Kraken' },
  { identifier: 'custom:ing', name: 'ING' },
  { identifier: 'custom:closed', name: 'Closed' },
];

function options(overrides: Partial<LocationOptionsInput>): string[] {
  return locationOptions({
    assignable: new Set(['kraken', 'custom:ing']),
    current: '',
    excludes: [],
    items: [],
    locations,
    pathOf: identifier => tree[identifier] ?? [],
    ...overrides,
  }).map(x => x.identifier);
}

describe('locationOptions', () => {
  it('should label an option with its path below the total', () => {
    expect(locationOptions({ assignable: undefined, current: '', excludes: [], items: ['custom:ing'], locations, pathOf: identifier => tree[identifier] ?? [] }))
      .toEqual([{ identifier: 'custom:ing', label: 'Banks › ING', name: 'ING', parentPath: 'Banks' }]);
  });

  it('should offer only where new data can go, keeping the current value of an old record', () => {
    expect(options({})).toEqual(['kraken', 'custom:ing']);
    expect(options({ current: 'custom:closed' })).toEqual(['kraken', 'custom:ing', 'custom:closed']);
  });

  it('should offer explicit items whatever their state, minus the excluded', () => {
    expect(options({ excludes: ['kraken'], items: ['kraken', 'custom:closed'] })).toEqual(['custom:closed']);
  });

  it('should offer explicit items in the order given, skipping unknown ones', () => {
    expect(options({ items: ['custom:ing', 'custom:missing', 'kraken'] })).toEqual(['custom:ing', 'kraken']);
  });

  it('should offer everything while the tree has not loaded', () => {
    expect(options({ assignable: undefined })).toEqual(['total', 'kraken', 'custom:ing', 'custom:closed']);
  });
});

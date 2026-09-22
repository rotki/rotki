import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { createLocationNode as node } from '@test/utils/location-tree';
import { describe, expect, it } from 'vitest';
import { locationRows } from '@/modules/locations/location-rows';

const children: Record<string, LocationNode[]> = {
  'total': [node('banks', 'total', 'Banks'), node('exchanges', 'total', 'Exchanges')],
  'banks': [node('custom:closed', 'banks', 'Closed', { isActive: false }), node('custom:ing', 'banks', 'ING')],
  'custom:ing': [node('custom:savings', 'custom:ing', 'Savings')],
  'exchanges': [node('kraken', 'exchanges', 'Kraken')],
};

function rows(showArchived: boolean, search = ''): [string, number, string][] {
  return locationRows({ childrenOf: identifier => children[identifier] ?? [], root: 'total', search, showArchived })
    .map(row => [row.node.identifier, row.depth, row.path]);
}

describe('locationRows', () => {
  it('should list the tree depth first with the path of every row', () => {
    expect(rows(true)).toEqual([
      ['banks', 0, 'Banks'],
      ['custom:closed', 1, 'Banks › Closed'],
      ['custom:ing', 1, 'Banks › ING'],
      ['custom:savings', 2, 'Banks › ING › Savings'],
      ['exchanges', 0, 'Exchanges'],
      ['kraken', 1, 'Exchanges › Kraken'],
    ]);
  });

  it('should hide archived locations unless asked', () => {
    expect(rows(false).map(([identifier]) => identifier)).not.toContain('custom:closed');
  });

  it('should keep the matches of a search with the ancestors leading to them', () => {
    expect(rows(false, 'saving').map(([identifier]) => identifier)).toEqual(['banks', 'custom:ing', 'custom:savings']);
    expect(rows(false, 'nothing')).toEqual([]);
  });
});

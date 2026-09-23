import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { describe, expect, it } from 'vitest';
import { bankLocations } from '@/modules/banks/bank-locations';

function node(identifier: string, parentIdentifier: string | null, name: string, isActive = true): LocationNode {
  return { icon: null, identifier, image: null, isActive, isBuiltin: !identifier.startsWith('custom:'), name, parentIdentifier };
}

describe('bankLocations', () => {
  it('should list every active bank below Banks, depth first and sorted by name', () => {
    expect(bankLocations([
      node('total', null, 'Total'),
      node('banks', 'total', 'Banks'),
      node('qonto', 'banks', 'Qonto'),
      node('custom:ing', 'banks', 'ING'),
      node('custom:savings', 'custom:ing', 'Savings'),
      node('custom:old', 'banks', 'Closed bank', false),
      node('custom:old-child', 'custom:old', 'Under a closed bank'),
      node('kraken', 'exchanges', 'Kraken'),
    ])).toEqual(['custom:ing', 'custom:savings', 'qonto']);
  });

  it('should list nothing before the tree has loaded', () => {
    expect(bankLocations([])).toEqual([]);
  });
});

import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { describe, expect, it } from 'vitest';
import { bankLocationOptions } from '@/modules/banks/bank-locations';

function node(identifier: string, parentIdentifier: string | null, name: string, isActive = true): LocationNode {
  return { icon: null, identifier, image: null, isActive, isBuiltin: !identifier.startsWith('custom:'), name, parentIdentifier };
}

describe('bankLocationOptions', () => {
  it('should list Banks and every active location below it, labelled by path', () => {
    expect(bankLocationOptions([
      node('total', null, 'Total'),
      node('banks', 'total', 'Banks'),
      node('qonto', 'banks', 'Qonto'),
      node('custom:ing', 'banks', 'ING'),
      node('custom:savings', 'custom:ing', 'Savings'),
      node('custom:old', 'banks', 'Closed bank', false),
      node('kraken', 'exchanges', 'Kraken'),
    ])).toEqual([
      { identifier: 'banks', label: 'Banks' },
      { identifier: 'qonto', label: 'Banks › Qonto' },
      { identifier: 'custom:ing', label: 'Banks › ING' },
      { identifier: 'custom:savings', label: 'Banks › ING › Savings' },
    ]);
  });

  it('should list nothing before the tree has loaded', () => {
    expect(bankLocationOptions([])).toEqual([]);
  });
});

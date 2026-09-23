import type { LocationNode } from '@/modules/locations/use-location-tree-api';
import { createLocationNode as node } from '@test/utils/location-tree';
import { describe, expect, it } from 'vitest';
import { locationRows, type LocationRowsInput, nameParts } from '@/modules/locations/location-rows';

const children: Record<string, LocationNode[]> = {
  'total': [node('banks', 'total', 'Banks'), node('exchanges', 'total', 'Exchanges')],
  'banks': [node('custom:closed', 'banks', 'Closed', { isActive: false }), node('custom:ing', 'banks', 'ING')],
  'custom:ing': [node('custom:savings', 'custom:ing', 'Savings')],
  'custom:closed': [node('custom:closed-child', 'custom:closed', 'Old account', { isActive: false })],
  'exchanges': [node('kraken', 'exchanges', 'Kraken')],
};

function build(overrides: Partial<LocationRowsInput>): ReturnType<typeof locationRows> {
  return locationRows({
    childrenOf: identifier => children[identifier] ?? [],
    isExpanded: () => true,
    root: 'total',
    search: '',
    showArchived: false,
    ...overrides,
  });
}

function identifiers(overrides: Partial<LocationRowsInput>): string[] {
  return build(overrides).map(row => row.node.identifier);
}

describe('locationRows', () => {
  it('should list the tree depth first with the path of every row', () => {
    expect(build({ showArchived: true }).map(row => [row.node.identifier, row.depth, row.path])).toEqual([
      ['banks', 0, 'Banks'],
      ['custom:closed', 1, 'Banks › Closed'],
      ['custom:closed-child', 2, 'Banks › Closed › Old account'],
      ['custom:ing', 1, 'Banks › ING'],
      ['custom:savings', 2, 'Banks › ING › Savings'],
      ['exchanges', 0, 'Exchanges'],
      ['kraken', 1, 'Exchanges › Kraken'],
    ]);
  });

  it('should hide archived locations unless asked', () => {
    expect(identifiers({})).not.toContain('custom:closed');
  });

  it('should keep listing an archived location it is told to keep, but not its archived children', () => {
    const listed = identifiers({ keepArchived: new Set(['custom:closed']) });
    expect(listed).toContain('custom:closed');
    expect(listed).not.toContain('custom:closed-child');
  });

  it('should keep the matches of a search with the ancestors leading to them', () => {
    expect(identifiers({ search: 'saving' })).toEqual(['banks', 'custom:ing', 'custom:savings']);
    expect(identifiers({ search: 'nothing' })).toEqual([]);
  });

  it('should hide the subtree of a collapsed location but keep the location itself', () => {
    expect(identifiers({ isExpanded: identifier => identifier !== 'banks' })).toEqual(['banks', 'exchanges', 'kraken']);
  });

  it('should open collapsed locations on the way to a search match', () => {
    expect(identifiers({ isExpanded: () => false, search: 'saving' })).toEqual(['banks', 'custom:ing', 'custom:savings']);
  });

  it('should mark a location as expandable only when it has rows that can show', () => {
    const byId = new Map(build({ isExpanded: () => false }).map(row => [row.node.identifier, row]));
    expect(byId.get('banks')).toMatchObject({ expanded: false, hasChildren: true });
    expect(byId.get('custom:closed')).toBeUndefined();

    const withArchived = new Map(build({ isExpanded: () => true, showArchived: true }).map(row => [row.node.identifier, row]));
    expect(withArchived.get('custom:closed')?.hasChildren).toBe(true);
    expect(withArchived.get('kraken')?.hasChildren).toBe(false);
  });
});

describe('nameParts', () => {
  it('should mark where a search matches a name, ignoring case', () => {
    expect(nameParts('Loopring', ' ING ')).toEqual([{ match: false, text: 'Loopr' }, { match: true, text: 'ing' }]);
    expect(nameParts('ING', 'ing')).toEqual([{ match: true, text: 'ING' }]);
  });

  it('should leave a name whole without a search or a match', () => {
    expect(nameParts('Kraken', '')).toEqual([{ match: false, text: 'Kraken' }]);
    expect(nameParts('Kraken', 'bank')).toEqual([{ match: false, text: 'Kraken' }]);
  });
});

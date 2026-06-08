import { describe, expect, it, vi } from 'vitest';
import { useHistoryEventHighlights } from './use-history-event-highlights';

// `mock`-prefixed so it can be referenced inside the hoisted vi.mock factory.
let mockQuery: Record<string, unknown> = {};

vi.mock('vue-router', () => ({
  useRoute: (): { query: Record<string, unknown> } => ({ query: mockQuery }),
}));

describe('useHistoryEventHighlights', () => {
  it('should expose nothing for an empty query', () => {
    mockQuery = {};
    const { highlightedGroupIdentifier, highlightedIdentifiers, highlightTypes } = useHistoryEventHighlights();
    expect(get(highlightedIdentifiers)).toBeUndefined();
    expect(get(highlightedGroupIdentifier)).toBeUndefined();
    expect(get(highlightTypes)).toEqual({});
  });

  it('should collect highlighted identifiers and map each to its colour', () => {
    mockQuery = {
      highlightedAssetMovement: '1',
      highlightedNegativeBalanceEvent: '2',
      highlightedPotentialMatch: '3',
    };
    const { highlightedIdentifiers, highlightTypes } = useHistoryEventHighlights();
    expect(get(highlightedIdentifiers)).toEqual(['1', '3', '2']);
    expect(get(highlightTypes)).toEqual({ 1: 'warning', 2: 'error', 3: 'success' });
  });

  it('should expose an internal-tx-conflict as a group highlight', () => {
    mockQuery = { highlightedInternalTxConflict: 'g1' };
    const { highlightedGroupIdentifier, highlightedIdentifiers, highlightTypes } = useHistoryEventHighlights();
    expect(get(highlightedGroupIdentifier)).toBe('g1');
    expect(get(highlightedIdentifiers)).toBeUndefined();
    expect(get(highlightTypes)).toEqual({ 'group:g1': 'warning' });
  });
});

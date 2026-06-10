import { describe, expect, it } from 'vitest';
import { splitHighlight } from '@/modules/history/events/action-picker/highlight-match';

describe('splitHighlight', () => {
  it('should return a single unmatched segment for an empty query', () => {
    expect(splitHighlight('Swap out', '')).toEqual([{ matched: false, text: 'Swap out' }]);
  });

  it('should return a single unmatched segment for a whitespace-only query', () => {
    expect(splitHighlight('Swap out', '   ')).toEqual([{ matched: false, text: 'Swap out' }]);
  });

  it('should wrap a case-insensitive match at the start of the label', () => {
    expect(splitHighlight('Swap out', 'swap')).toEqual([
      { matched: true, text: 'Swap' },
      { matched: false, text: ' out' },
    ]);
  });

  it('should wrap a match in the middle of the label', () => {
    expect(splitHighlight('Receive reward', 'eward')).toEqual([
      { matched: false, text: 'Receive r' },
      { matched: true, text: 'eward' },
    ]);
  });

  it('should preserve the original casing of the matched span', () => {
    expect(splitHighlight('Deposit Asset', 'DEPOSIT')).toEqual([
      { matched: true, text: 'Deposit' },
      { matched: false, text: ' Asset' },
    ]);
  });

  it('should return the whole label unmatched when there is no contiguous match', () => {
    expect(splitHighlight('Swap out', 'wapou')).toEqual([{ matched: false, text: 'Swap out' }]);
  });
});

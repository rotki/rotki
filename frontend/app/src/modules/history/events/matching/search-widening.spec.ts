import { describe, expect, it } from 'vitest';
import {
  canWidenSearch,
  MAX_SEARCH_HOURS,
  MAX_TOLERANCE_PERCENTAGE,
  widenedSearch,
} from '@/modules/history/events/matching/search-widening';

describe('canWidenSearch', () => {
  it('should offer to widen while both criteria have room', () => {
    expect(canWidenSearch({ hours: '24', tolerance: '5' })).toBe(true);
  });

  it('should offer to widen while only the time range has room', () => {
    expect(canWidenSearch({ hours: '24', tolerance: '100' })).toBe(true);
  });

  it('should offer to widen while only the tolerance has room', () => {
    expect(canWidenSearch({ hours: '168', tolerance: '5' })).toBe(true);
  });

  it('should stop offering once both criteria are at their max', () => {
    expect(canWidenSearch({ hours: '168', tolerance: '100' })).toBe(false);
  });

  it('should stop offering once both criteria are past their max', () => {
    expect(canWidenSearch({ hours: '500', tolerance: '400' })).toBe(false);
  });

  it('should stop offering when neither criterion is a number', () => {
    expect(canWidenSearch({ hours: 'abc', tolerance: 'abc' })).toBe(false);
  });

  /** An empty field is zero, not unparsable, so the control stays offered. */
  it('should keep offering while a criterion is empty', () => {
    expect(canWidenSearch({ hours: '', tolerance: 'abc' })).toBe(true);
  });
});

describe('widenedSearch', () => {
  it('should double both criteria', () => {
    expect(widenedSearch({ hours: '12', tolerance: '5' })).toEqual({ hours: '24', tolerance: '10' });
  });

  it('should cap the time range at its max', () => {
    expect(widenedSearch({ hours: '120', tolerance: '5' }).hours).toBe(String(MAX_SEARCH_HOURS));
  });

  it('should cap the tolerance at its max', () => {
    expect(widenedSearch({ hours: '12', tolerance: '80' }).tolerance).toBe(String(MAX_TOLERANCE_PERCENTAGE));
  });

  it('should leave a criterion already at its max alone', () => {
    expect(widenedSearch({ hours: '168', tolerance: '100' })).toEqual({ hours: '168', tolerance: '100' });
  });

  /** Widening must not throw away what the user was in the middle of entering. */
  it('should leave a criterion that does not parse exactly as typed', () => {
    expect(widenedSearch({ hours: '1e', tolerance: '5' })).toEqual({ hours: '1e', tolerance: '10' });
  });

  /** Doubling zero is zero, so an emptied field stays put while the other one grows. */
  it('should leave a zero criterion at zero', () => {
    expect(widenedSearch({ hours: '0', tolerance: '5' })).toEqual({ hours: '0', tolerance: '10' });
  });

  it('should read an empty criterion as zero', () => {
    expect(widenedSearch({ hours: '', tolerance: '5' }).hours).toBe('0');
  });
});

import { describe, expect, it } from 'vitest';
import { includes, isFilterEnabled, sortBy } from './account-common';

describe('sortBy', () => {
  it('should sort numbers ascending', () => {
    expect(sortBy(1, 2, true)).toBeLessThan(0);
    expect(sortBy(2, 1, true)).toBeGreaterThan(0);
    expect(sortBy(2, 2, true)).toBe(0);
  });

  it('should sort numbers descending', () => {
    expect(sortBy(1, 2, false)).toBeGreaterThan(0);
    expect(sortBy(2, 1, false)).toBeLessThan(0);
  });

  it('should treat numeric strings as numbers', () => {
    expect(sortBy('10', '9', true)).toBeGreaterThan(0);
    expect(sortBy('10', '9', false)).toBeLessThan(0);
  });

  it('should sort strings using locale comparison', () => {
    expect(sortBy('apple', 'banana', true)).toBeLessThan(0);
    expect(sortBy('banana', 'apple', true)).toBeGreaterThan(0);
  });

  it('should reverse string comparison when descending', () => {
    expect(sortBy('apple', 'banana', false)).toBeGreaterThan(0);
  });

  it('should compare case-insensitively for accent sensitivity', () => {
    expect(sortBy('Apple', 'apple', true)).toBe(0);
  });
});

describe('isFilterEnabled', () => {
  it('should return false for undefined', () => {
    expect(isFilterEnabled(undefined)).toBe(false);
  });

  it('should return false for an empty string', () => {
    expect(isFilterEnabled('')).toBe(false);
  });

  it('should return true for a non-empty string', () => {
    expect(isFilterEnabled('active')).toBe(true);
  });

  it('should return false for an empty array', () => {
    expect(isFilterEnabled([])).toBe(false);
  });

  it('should return true for a non-empty array', () => {
    expect(isFilterEnabled(['active'])).toBe(true);
  });
});

describe('includes', () => {
  it('should match case-insensitively', () => {
    expect(includes('Ethereum', 'ether')).toBe(true);
    expect(includes('ethereum', 'ETHER')).toBe(true);
  });

  it('should return false when the search term is absent', () => {
    expect(includes('Ethereum', 'bitcoin')).toBe(false);
  });

  it('should return true for an empty search term', () => {
    expect(includes('Ethereum', '')).toBe(true);
  });
});

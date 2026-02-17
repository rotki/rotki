import { describe, expect, it } from 'vitest';
import { groupConsecutiveNumbers } from './text';

describe('groupConsecutiveNumbers', () => {
  it('returns empty string for empty array', () => {
    expect(groupConsecutiveNumbers([])).toBe('');
  });

  it('handles a single number', () => {
    expect(groupConsecutiveNumbers([5])).toBe('5');
  });

  it('handles consecutive numbers as a range', () => {
    expect(groupConsecutiveNumbers([1, 2, 3])).toBe('1-3');
  });

  it('handles non-consecutive numbers as individual values', () => {
    expect(groupConsecutiveNumbers([1, 3, 5])).toBe('1, 3, 5');
  });

  it('handles mixed consecutive and non-consecutive numbers', () => {
    expect(groupConsecutiveNumbers([1, 2, 3, 5, 7, 10, 11, 12, 13])).toBe('1-3, 5, 7, 10-13');
  });

  it('handles two consecutive numbers', () => {
    expect(groupConsecutiveNumbers([4, 5])).toBe('4-5');
  });

  it('handles multiple separate ranges', () => {
    expect(groupConsecutiveNumbers([1, 2, 5, 6, 9, 10])).toBe('1-2, 5-6, 9-10');
  });

  it('handles a single range followed by individual numbers', () => {
    expect(groupConsecutiveNumbers([1, 2, 3, 7, 9])).toBe('1-3, 7, 9');
  });

  it('handles individual numbers followed by a range', () => {
    expect(groupConsecutiveNumbers([1, 5, 8, 9, 10])).toBe('1, 5, 8-10');
  });
});

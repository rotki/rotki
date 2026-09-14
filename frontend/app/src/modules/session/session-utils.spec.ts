import { describe, expect, it } from 'vitest';
import { generateRandomScrambleMultiplier, normalizeScrambleMultiplier } from './session-utils';

describe('normalizeScrambleMultiplier', () => {
  it.each([0.001, 0.123, 0.5, 0.999])('should keep %s below 1 as given', (multiplier) => {
    expect(normalizeScrambleMultiplier(multiplier)).toBe(multiplier);
  });

  it.each([1, 3, 7.25])('should keep %s as given', (multiplier) => {
    expect(normalizeScrambleMultiplier(multiplier)).toBe(multiplier);
  });

  it.each([0, -0.5, -3, Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    'should fall back to 1 for %s',
    (multiplier) => {
      expect(normalizeScrambleMultiplier(multiplier)).toBe(1);
    },
  );
});

describe('generateRandomScrambleMultiplier', () => {
  it('should stay within [1, 10]', () => {
    for (let i = 0; i < 1000; i++) {
      const multiplier = generateRandomScrambleMultiplier();
      expect(multiplier).toBeGreaterThanOrEqual(1);
      expect(multiplier).toBeLessThanOrEqual(10);
    }
  });
});

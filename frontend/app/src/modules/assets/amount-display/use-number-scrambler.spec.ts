import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { useNumberScrambler } from './use-number-scrambler';

/**
 * The seam: the single place a displayed amount is scrambled, reached by every amount component
 * through `use-scrambled-value` and directly by the statistics store. It is handed an unvalidated
 * user setting, so these tests pin what it does with a bad one.
 */
describe('useNumberScrambler', () => {
  const value = bigNumberify(1234.5);

  it('should return the value untouched when scrambling is off', () => {
    const scrambled = useNumberScrambler({ enabled: false, multiplier: 0, value });

    expect(get(scrambled).toString()).toBe('1234.5');
  });

  it('should never render a scrambled amount as zero', () => {
    const scrambled = useNumberScrambler({ enabled: true, multiplier: 0, value });

    expect(get(scrambled).isZero()).toBe(false);
  });

  it('should not render a scrambled amount smaller than the real one', () => {
    const scrambled = useNumberScrambler({ enabled: true, multiplier: 0.5, value });

    expect(get(scrambled).isGreaterThanOrEqualTo(value)).toBe(true);
  });

  it('should still scramble with a valid multiplier', () => {
    const scrambled = useNumberScrambler({ enabled: true, multiplier: 3, value });

    expect(get(scrambled).toString()).toBe('3703.5');
  });
});

import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { useNumberScrambler } from './use-number-scrambler';

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

  it('should scramble with a multiplier below 1 as given', () => {
    const scrambled = useNumberScrambler({ enabled: true, multiplier: 0.5, value });

    expect(get(scrambled).toString()).toBe('617.25');
  });

  it('should never flip the sign of a scrambled amount', () => {
    const scrambled = useNumberScrambler({ enabled: true, multiplier: -2, value });

    expect(get(scrambled).toString()).toBe('1234.5');
  });

  it('should still scramble with a valid multiplier', () => {
    const scrambled = useNumberScrambler({ enabled: true, multiplier: 3, value });

    expect(get(scrambled).toString()).toBe('3703.5');
  });
});

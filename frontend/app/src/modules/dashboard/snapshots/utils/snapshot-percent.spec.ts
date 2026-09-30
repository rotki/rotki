import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { formatPercent } from '@/modules/dashboard/snapshots/utils/snapshot-percent';

describe('modules/dashboard/snapshots/utils/snapshot-percent', () => {
  it('should format an ordinary percentage with the given decimals', () => {
    expect(formatPercent(bigNumberify('12.345'), 2)).toBe('12.35');
    expect(formatPercent(-4.4, 0)).toBe('-4');
  });

  it('should keep a percentage at the limit', () => {
    expect(formatPercent(1_000_000, 0)).toBe('1,000,000');
  });

  it('should cap a percentage beyond the limit instead of printing every digit', () => {
    expect(formatPercent(bigNumberify('2976639035418236623963828183873.40'), 2)).toBe('>1,000,000');
  });

  it('should cap a number that would otherwise print in exponent notation', () => {
    expect(formatPercent(2.9766390354182366e30, 0)).toBe('>1,000,000');
    expect(formatPercent(-2.9766390354182366e30, 0)).toBe('<-1,000,000');
  });
});

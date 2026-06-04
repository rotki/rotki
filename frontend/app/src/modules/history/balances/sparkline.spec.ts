import { describe, expect, it } from 'vitest';
import { downsample, SPARKLINE_MAX_POINTS } from './sparkline';

describe('sparkline downsample', () => {
  it('should return the input unchanged when within the cap', () => {
    expect(downsample([1, 2, 3], 5)).toEqual([1, 2, 3]);
  });

  it('should keep the first and last entries when subsampling', () => {
    const input = Array.from({ length: 100 }, (_, i) => i);
    const result = downsample(input, 10);
    expect(result).toHaveLength(10);
    expect(result[0]).toBe(0);
    expect(result.at(-1)).toBe(99);
  });

  it('should subsample uniformly', () => {
    const input = Array.from({ length: 9 }, (_, i) => i);
    expect(downsample(input, 5)).toEqual([0, 2, 4, 6, 8]);
  });

  it('should cap a long series to SPARKLINE_MAX_POINTS', () => {
    const input = Array.from({ length: 500 }, (_, i) => i);
    const result = downsample(input, SPARKLINE_MAX_POINTS);
    expect(result).toHaveLength(SPARKLINE_MAX_POINTS);
    expect(result[0]).toBe(0);
    expect(result.at(-1)).toBe(499);
  });
});

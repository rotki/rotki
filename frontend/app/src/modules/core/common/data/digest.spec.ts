import { describe, expect, it } from 'vitest';
import { setDigest } from '@/modules/core/common/data/digest';

describe('setDigest', () => {
  it('should be independent of member order', () => {
    expect(setDigest(['ETH', 'DAI', 'BTC'])).toBe(setDigest(['BTC', 'ETH', 'DAI']));
  });

  it('should differ for different sets', () => {
    expect(setDigest(['DAI'])).not.toBe(setDigest(['ETH']));
    expect(setDigest(['DAI'])).not.toBe(setDigest(['DAI', 'ETH']));
  });

  it('should not collide on a shifted separator, an unfolded one making [ab, c] and [a, bc] the same byte stream', () => {
    expect(setDigest(['ab', 'c'])).not.toBe(setDigest(['a', 'bc']));
  });
});

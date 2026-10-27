import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { hasAwaitingClaim } from '@/modules/core/common/display/balances';

describe('hasAwaitingClaim', () => {
  it('should be true when part of the balance awaits a claim', () => {
    expect(hasAwaitingClaim({ awaitingClaim: bigNumberify('0.5') })).toBe(true);
  });

  it('should be false when nothing awaits a claim', () => {
    expect(hasAwaitingClaim({})).toBe(false);
    expect(hasAwaitingClaim({ awaitingClaim: bigNumberify(0) })).toBe(false);
  });
});

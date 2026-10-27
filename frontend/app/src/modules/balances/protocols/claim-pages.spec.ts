import { describe, expect, it } from 'vitest';
import { claimPageUrl } from '@/modules/balances/protocols/claim-pages';

describe('claimPageUrl', () => {
  it('should return the page where lido and venice withdrawals are claimed', () => {
    expect(claimPageUrl('lido')).toBe('https://stake.lido.fi/withdrawals/claim');
    expect(claimPageUrl('venice')).toBe('https://venice.ai/token');
  });

  it('should return nothing for a protocol without a claim page', () => {
    expect(claimPageUrl('uniswap-v3')).toBeUndefined();
  });
});

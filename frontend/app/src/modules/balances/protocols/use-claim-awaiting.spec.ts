import { bigNumberify, type ClaimRequest, type ProtocolBalance } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { claimAccounts, isClaimReady, useClaimAwaiting } from '@/modules/balances/protocols/use-claim-awaiting';

function claim(overrides: Partial<ClaimRequest> = {}): ClaimRequest {
  return { amount: bigNumberify(1), finalized: false, ...overrides };
}

describe('isClaimReady', () => {
  it('should be ready once the protocol finalized the request', () => {
    expect(isClaimReady(claim({ finalized: true }), 100)).toBe(true);
  });

  it('should be ready only after the wait is over', () => {
    expect(isClaimReady(claim({ availableAt: 200 }), 199)).toBe(false);
    expect(isClaimReady(claim({ availableAt: 200 }), 200)).toBe(true);
  });

  it('should stay pending when nothing says it can be claimed', () => {
    expect(isClaimReady(claim({ requestedAt: 50 }), 100)).toBe(false);
  });
});

describe('claimAccounts', () => {
  it('should list each account once and ignore requests without one', () => {
    const accounts = claimAccounts([
      claim({ account: { address: '0xA', chain: 'eth' } }),
      claim({ account: { address: '0xA', chain: 'eth' } }),
      claim({ account: { address: '0xA', chain: 'base' } }),
      claim(),
    ]);

    expect(accounts).toEqual([{ address: '0xA', chain: 'eth' }, { address: '0xA', chain: 'base' }]);
  });
});

describe('useClaimAwaiting', () => {
  function balance(claims?: ClaimRequest[]): ProtocolBalance {
    return { amount: bigNumberify(1), claims, protocol: 'lido', value: bigNumberify(1) };
  }

  it('should report a ready request when any request can be claimed', () => {
    const { hasReady } = useClaimAwaiting(() => balance([claim(), claim({ finalized: true })]));

    expect(hasReady.value).toBe(true);
  });

  it('should report nothing ready while every request is still pending', () => {
    const { hasReady, isReady } = useClaimAwaiting(() => balance([claim({ availableAt: 4_102_444_800 })]));

    expect(hasReady.value).toBe(false);
    expect(isReady(claim({ availableAt: 1 }))).toBe(true);
  });

  it('should list the requests oldest first whatever order they arrive in', () => {
    const { claims } = useClaimAwaiting(() => balance([
      claim({ id: '3', requestedAt: 30 }),
      claim({ id: '1', requestedAt: 10 }),
      claim({ id: '2', requestedAt: 20 }),
    ]));

    expect(claims.value.map(({ id }) => id)).toEqual(['1', '2', '3']);
  });

  it('should have no requests for a balance recorded before they were stored', () => {
    const { accounts, claims } = useClaimAwaiting(() => balance());

    expect(claims.value).toEqual([]);
    expect(accounts.value).toEqual([]);
  });
});

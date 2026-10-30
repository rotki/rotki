import { bigNumberify, type ClaimRequest, type ProtocolBalance } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { claimAccounts, claimStatus, isClaimReady, useClaimAwaiting } from '@/modules/balances/protocols/use-claim-awaiting';

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

describe('claimStatus', () => {
  it('should be ready as soon as one request is ready', () => {
    expect(claimStatus([claim({ availableAt: 500 }), claim({ finalized: true })], 100)).toEqual({ kind: 'ready' });
  });

  it('should unlock at the earliest date when every pending request has one', () => {
    expect(claimStatus([claim({ availableAt: 500 }), claim({ availableAt: 300 })], 100))
      .toEqual({ availableAt: 300, kind: 'unlocks' });
  });

  it('should be pending when a pending request has no unlock date', () => {
    expect(claimStatus([claim({ availableAt: 300 }), claim({ requestedAt: 50 })], 100)).toEqual({ kind: 'pending' });
  });

  it('should be pending when there are no requests', () => {
    expect(claimStatus([], 100)).toEqual({ kind: 'pending' });
  });
});

describe('useClaimAwaiting', () => {
  function balance(claims?: ClaimRequest[]): ProtocolBalance {
    return { amount: bigNumberify(1), claims, protocol: 'lido', value: bigNumberify(1) };
  }

  it('should be ready, with only the ready amount, when any request can be claimed', () => {
    const { status, statusAmount } = useClaimAwaiting(() => ({
      ...balance([claim({ amount: bigNumberify(2) }), claim({ amount: bigNumberify(3), finalized: true })]),
      awaitingClaim: bigNumberify(5),
    }));

    expect(status.value).toEqual({ kind: 'ready' });
    expect(statusAmount.value).toEqual(bigNumberify(3));
  });

  it('should count everything awaiting a claim while nothing is ready', () => {
    const { isReady, status, statusAmount } = useClaimAwaiting(() => ({
      ...balance([claim({ availableAt: 4_102_444_800 })]),
      awaitingClaim: bigNumberify(1),
    }));

    expect(status.value).toEqual({ availableAt: 4_102_444_800, kind: 'unlocks' });
    expect(statusAmount.value).toEqual(bigNumberify(1));
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

import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type BigNumber, type ClaimAccount, type ClaimRequest, type ProtocolBalance, Zero } from '@rotki/common';
import { useIntervalFn, useNow } from '@vueuse/core';
import { compareClaims } from '@/modules/balances/aggregation/core/balance-entry';

const CLAIM_READINESS_TICK_MS = 30_000;

/** Whether the protocol already lets the user claim the request: it is finalized, or its wait is over. */
export function isClaimReady(claim: ClaimRequest, nowInSeconds: number): boolean {
  return claim.finalized || (claim.availableAt !== undefined && claim.availableAt <= nowInSeconds);
}

/** The accounts that own the requests, each once, in the order they are first met. */
export function claimAccounts(claims: readonly ClaimRequest[]): ClaimAccount[] {
  const accounts = new Map<string, ClaimAccount>();
  for (const { account } of claims) {
    if (account)
      accounts.set(`${account.chain}:${account.address}`, account);
  }
  return [...accounts.values()];
}

/**
 * What the claim chip says: `ready` once any request can be claimed, `unlocks` with the earliest
 * date when every pending request has one, otherwise `pending`.
 */
export type ClaimStatus =
  | { kind: 'ready' }
  | { kind: 'unlocks'; availableAt: number }
  | { kind: 'pending' };

/** The status of a set of requests at `nowInSeconds`. */
export function claimStatus(claims: readonly ClaimRequest[], nowInSeconds: number): ClaimStatus {
  const pending = claims.filter(claim => !isClaimReady(claim, nowInSeconds));
  if (pending.length < claims.length)
    return { kind: 'ready' };

  const unlockTimes: number[] = [];
  for (const { availableAt } of pending) {
    if (availableAt === undefined)
      return { kind: 'pending' };
    unlockTimes.push(availableAt);
  }

  return unlockTimes.length > 0 ? { availableAt: Math.min(...unlockTimes), kind: 'unlocks' } : { kind: 'pending' };
}

interface UseClaimAwaitingReturn {
  claims: ComputedRef<ClaimRequest[]>;
  accounts: ComputedRef<ClaimAccount[]>;
  status: ComputedRef<ClaimStatus>;
  /** What can be claimed right now, or everything awaiting a claim while nothing is ready yet. */
  statusAmount: ComputedRef<BigNumber>;
  isReady: (claim: ClaimRequest) => boolean;
}

/**
 * Describes what the user has to claim from one protocol balance.
 *
 * @remarks
 * Readiness is worked out against the current time instead of being stored, because the balances
 * are cached and a wait that ends in the meantime would otherwise stay pending until a refresh.
 */
export function useClaimAwaiting(protocolBalance: MaybeRefOrGetter<ProtocolBalance>): UseClaimAwaitingReturn {
  const now = useNow({ scheduler: tick => useIntervalFn(tick, CLAIM_READINESS_TICK_MS) });
  const nowInSeconds = computed<number>(() => Math.floor(get(now).getTime() / 1000));

  const claims = computed<ClaimRequest[]>(() => [...toValue(protocolBalance).claims ?? []].sort(compareClaims));
  const accounts = computed<ClaimAccount[]>(() => claimAccounts(get(claims)));

  function isReady(claim: ClaimRequest): boolean {
    return isClaimReady(claim, get(nowInSeconds));
  }

  const status = computed<ClaimStatus>(() => claimStatus(get(claims), get(nowInSeconds)));

  const statusAmount = computed<BigNumber>(() => {
    if (get(status).kind !== 'ready')
      return toValue(protocolBalance).awaitingClaim ?? Zero;

    return get(claims).filter(isReady).reduce((total, { amount }) => total.plus(amount), Zero);
  });

  return { accounts, claims, isReady, status, statusAmount };
}

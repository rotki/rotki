import type { ClaimAccount, ClaimRequest, ProtocolBalance } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
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

interface UseClaimAwaitingReturn {
  claims: ComputedRef<ClaimRequest[]>;
  accounts: ComputedRef<ClaimAccount[]>;
  /** At least one request can be claimed right now. */
  hasReady: ComputedRef<boolean>;
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

  const hasReady = computed<boolean>(() => get(claims).some(isReady));

  return { accounts, claims, hasReady, isReady };
}

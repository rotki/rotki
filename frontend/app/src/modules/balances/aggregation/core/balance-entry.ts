import { type Balance, type ClaimRequest, Zero } from '@rotki/common';
import { balanceSum } from '@/modules/core/common/data/calculation';

/** A balance held under one protocol, possibly merged from several sources, chains or assets. */
export type BalanceEntry = Balance & {
  awaitingClaim?: Balance['amount'];
  /** The withdrawal requests that make up `awaitingClaim`. */
  claims?: ClaimRequest[];
  /** Some of it comes from a balance the user entered manually. */
  containsManual?: boolean;
  /** The per-chain split, carried by the on-chain `address` protocol only. */
  chains?: Record<string, Balance>;
};

function mergeChains(
  a: Record<string, Balance> | undefined,
  b: Record<string, Balance> | undefined,
): Record<string, Balance> | undefined {
  if (!a || !b)
    return a ?? b;

  const merged = { ...a };
  for (const [chain, balance] of Object.entries(b))
    merged[chain] = merged[chain] ? balanceSum(merged[chain], balance) : balance;

  return merged;
}

function claimSortKey(claim: ClaimRequest): string {
  const time = String(claim.requestedAt ?? claim.availableAt ?? 0).padStart(12, '0');
  return [time, claim.id ?? '', claim.account?.chain ?? '', claim.account?.address ?? ''].join('|');
}

/** Oldest first, so the merged list does not depend on which side came first. */
export function compareClaims(a: ClaimRequest, b: ClaimRequest): number {
  return claimSortKey(a).localeCompare(claimSortKey(b));
}

function mergeClaims(a: ClaimRequest[] | undefined, b: ClaimRequest[] | undefined): ClaimRequest[] | undefined {
  if (!a || !b)
    return a ?? b;

  return [...a, ...b].sort(compareClaims);
}

/**
 * Merges two entries for the same asset and protocol.
 *
 * @remarks
 * The only place the merge rule lives. It is commutative and associative, so the result does not
 * depend on which source, chain or collection member is read first. Neither input is modified.
 */
export function combineBalanceEntries(a: BalanceEntry, b: BalanceEntry): BalanceEntry {
  const chains = mergeChains(a.chains, b.chains);
  const claims = mergeClaims(a.claims, b.claims);
  return {
    ...balanceSum(a, b),
    ...(a.awaitingClaim || b.awaitingClaim
      ? { awaitingClaim: (a.awaitingClaim ?? Zero).plus(b.awaitingClaim ?? Zero) }
      : {}),
    ...(claims ? { claims } : {}),
    ...(chains ? { chains } : {}),
    ...(a.containsManual || b.containsManual ? { containsManual: true } : {}),
  };
}

/**
 * Adds `entry` under `key`, combining it with whatever is already there.
 *
 * @remarks
 * Writes into `into`, which the caller must own: an accumulator it created, never store state.
 */
export function addBalanceEntry(into: Record<string, BalanceEntry>, key: string, entry: BalanceEntry): void {
  const existing = into[key];
  into[key] = existing ? combineBalanceEntries(existing, entry) : entry;
}

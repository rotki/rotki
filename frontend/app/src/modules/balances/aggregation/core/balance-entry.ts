import { type Balance, type ClaimAccount, Zero } from '@rotki/common';
import { balanceSum } from '@/modules/core/common/data/calculation';

/** A balance held under one protocol, possibly merged from several sources, chains or assets. */
export type BalanceEntry = Balance & {
  awaitingClaim?: Balance['amount'];
  /** The accounts holding `awaitingClaim`. */
  awaitingClaimAccounts?: ClaimAccount[];
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

function mergeClaimAccounts(a: ClaimAccount[] | undefined, b: ClaimAccount[] | undefined): ClaimAccount[] | undefined {
  if (!a || !b)
    return a ?? b;

  const merged = [...a];
  for (const account of b) {
    if (!merged.some(({ address, chain }) => address === account.address && chain === account.chain))
      merged.push(account);
  }
  return merged.sort((x, y) => x.chain.localeCompare(y.chain) || x.address.localeCompare(y.address));
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
  const awaitingClaimAccounts = mergeClaimAccounts(a.awaitingClaimAccounts, b.awaitingClaimAccounts);
  return {
    ...balanceSum(a, b),
    ...(a.awaitingClaim || b.awaitingClaim
      ? { awaitingClaim: (a.awaitingClaim ?? Zero).plus(b.awaitingClaim ?? Zero) }
      : {}),
    ...(awaitingClaimAccounts ? { awaitingClaimAccounts } : {}),
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

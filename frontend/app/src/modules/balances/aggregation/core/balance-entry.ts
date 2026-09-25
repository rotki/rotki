import type { Balance } from '@rotki/common';
import { balanceSum } from '@/modules/core/common/data/calculation';

/** A balance held under one protocol, possibly merged from several sources, chains or assets. */
export type BalanceEntry = Balance & {
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

/**
 * Merges two entries for the same asset and protocol.
 *
 * @remarks
 * The only place the merge rule lives. It is commutative and associative, so the result does not
 * depend on which source, chain or collection member is read first. Neither input is modified.
 */
export function combineBalanceEntries(a: BalanceEntry, b: BalanceEntry): BalanceEntry {
  const chains = mergeChains(a.chains, b.chains);
  return {
    ...balanceSum(a, b),
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

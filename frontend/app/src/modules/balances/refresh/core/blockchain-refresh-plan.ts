import { partition, unique } from 'plainfp/arrays';

export interface BlockchainRefreshPlan {
  /** Chains whose balances come from token detection. */
  readonly detect: readonly string[];
  /** Chains whose balances come from a balance query. */
  readonly query: readonly string[];
}

interface PlanInput {
  readonly chains: readonly string[];
  readonly redetect: boolean;
  readonly supportsDetection: (chain: string) => boolean;
}

/**
 * Splits a blockchain refresh between detection and querying.
 *
 * @remarks
 * Detection writes the balances it finds, so it refreshes a chain on its own. It only covers some
 * chains, though: redetecting everything used to leave Bitcoin and the other chains detection skips
 * with stale balances. Those are queried instead, and no chain is both detected and queried.
 */
export function planBlockchainRefresh({ chains, redetect, supportsDetection }: PlanInput): BlockchainRefreshPlan {
  const requested = unique(chains);
  if (!redetect)
    return { detect: [], query: requested };

  const [detect, query] = partition(requested, supportsDetection);
  return { detect, query };
}

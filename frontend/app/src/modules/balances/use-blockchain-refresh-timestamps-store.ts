import type { ComputedRef } from 'vue';
import { byChainKey, toChainKey } from '@/modules/core/common/chains';

export const useBlockchainRefreshTimestampsStore = defineStore('balances/refresh-timestamps', () => {
  /** Keyed by snake_case chain id ({@link toChainKey}), whatever spelling the writer used. */
  const refreshTimestamps = ref<Record<string, number>>({});

  /**
   * Monotonic per chain: a timestamp older than the one already stored is ignored.
   *
   * Two independent things write a chain's balances, a read from the DB and a network query, and
   * they are deliberately allowed to overlap. The timestamp only settles part of that ordering; see
   * {@link isStale} for what it cannot tell.
   */
  const updateTimestamps = (timestamps: Record<string, number>): void => {
    const current = get(refreshTimestamps);
    const next = { ...current };
    let changed = false;

    for (const [chain, timestamp] of Object.entries(byChainKey(timestamps))) {
      const stored = next[chain];
      if (stored !== undefined && stored >= timestamp)
        continue;

      next[chain] = timestamp;
      changed = true;
    }

    if (changed)
      set(refreshTimestamps, next);
  };

  /**
   * Whether an incoming payload for this chain is older than what has already been stored.
   *
   * Only ever `true` when both sides are known. A payload with no timestamp is accepted: the
   * backend omits `last_refresh_ts` when the chain has never been queried, when its last query
   * stored no balances, and after its accounts or validators changed.
   *
   * @remarks
   * Not sufficient for a cached read that overlaps a network result. The backend reads the timestamp
   * after the balances, so such a read can carry the newer query's timestamp with older data, and a
   * tie cannot be refused because a deliberate re-read (an un-ignored asset, detected tokens)
   * legitimately has the same timestamp and different content. `handleCachedFetch` covers that case
   * by comparing when the read began instead.
   */
  const isStale = (chain: string, timestamp: number | undefined): boolean => {
    if (timestamp === undefined)
      return false;

    const stored = get(refreshTimestamps)[toChainKey(chain)];
    return stored !== undefined && timestamp < stored;
  };

  const getTimestamp = (chain: string): ComputedRef<number | undefined> =>
    computed<number | undefined>(() => get(refreshTimestamps)[toChainKey(chain)]);

  const reset = (): void => {
    set(refreshTimestamps, {});
  };

  return { getTimestamp, isStale, refreshTimestamps, reset, updateTimestamps };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainRefreshTimestampsStore, import.meta.hot));

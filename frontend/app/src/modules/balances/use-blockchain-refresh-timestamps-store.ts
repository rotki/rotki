import type { ComputedRef } from 'vue';

export const useBlockchainRefreshTimestampsStore = defineStore('balances/refresh-timestamps', () => {
  const refreshTimestamps = ref<Record<string, number>>({});

  /**
   * Monotonic per chain: a timestamp older than the one already stored is ignored.
   *
   * Two independent things write a chain's balances — a data refresh from the DB and a network
   * query — and they are deliberately allowed to overlap. Merging blindly meant whichever *landed*
   * last won, so a slow local read finishing after a fresh network result would roll the chain back
   * to stale data. Keeping the newest timestamp is what makes the ordering irrelevant, so nothing
   * has to serialise the two.
   */
  const updateTimestamps = (timestamps: Record<string, number>): void => {
    const current = get(refreshTimestamps);
    const next = { ...current };
    let changed = false;

    for (const [chain, timestamp] of Object.entries(timestamps)) {
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
   * backend omits `last_refresh_ts` when it has never queried the chain, and refusing those would
   * mean a chain that has never been refreshed can never receive its first balances.
   */
  const isStale = (chain: string, timestamp: number | undefined): boolean => {
    if (timestamp === undefined)
      return false;

    const stored = get(refreshTimestamps)[chain];
    return stored !== undefined && timestamp < stored;
  };

  const getTimestamp = (chain: string): ComputedRef<number | undefined> =>
    computed<number | undefined>(() => get(refreshTimestamps)[chain]);

  const reset = (): void => {
    set(refreshTimestamps, {});
  };

  return { getTimestamp, isStale, refreshTimestamps, reset, updateTimestamps };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBlockchainRefreshTimestampsStore, import.meta.hot));

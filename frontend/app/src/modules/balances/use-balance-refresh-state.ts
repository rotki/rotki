import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';

function addChain(chains: Ref<Set<string>>, chain: string): void {
  const current = get(chains);
  if (current.has(chain))
    return;
  const next = new Set(current);
  next.add(chain);
  set(chains, next);
}

function removeChain(chains: Ref<Set<string>>, chain: string): void {
  const current = get(chains);
  if (!current.has(chain))
    return;
  const next = new Set(current);
  next.delete(chain);
  set(chains, next);
}

/**
 * Which chains have balance work in flight: `refreshingChains` for the network query,
 * `hydratingChains` for the read from the user's own database.
 *
 * @remarks
 * Kept apart because a row's refresh spinner belongs to the first, while "nothing to show yet"
 * belongs to both. Read them through `useBalancesLoading` rather than from here.
 *
 * `firstLoadSettled` is the session-wide latch for the login load: it flips once that load's chain
 * and price refreshes have settled, or at once for a restored session that fetches nothing, and
 * stays set until logout. Readers that would misreport a half-loaded state wait on it.
 */
export const useBalanceRefreshState = defineStore('balances/refresh-state', () => {
  const refreshingChains = ref<Set<string>>(new Set());
  const hydratingChains = ref<Set<string>>(new Set());
  const firstLoadSettled = ref<boolean>(false);
  const appliedNetworkResults = new Map<string, number>();

  /**
   * How many network results have been applied to this chain's balances this session.
   *
   * @remarks
   * Not reactive, because only the cached-read guard in `useBalanceProcessingService` compares it.
   * A count that moved while a cached read was in flight means that read began before the network
   * result landed, which timestamps cannot tell: see `isStale`.
   */
  const networkResultCount = (chain: string): number => appliedNetworkResults.get(chain) ?? 0;

  const markNetworkResultApplied = (chain: string): void => {
    appliedNetworkResults.set(chain, networkResultCount(chain) + 1);
  };

  const start = (chain: string): void => {
    addChain(refreshingChains, chain);
  };

  const stop = (chain: string): void => {
    removeChain(refreshingChains, chain);
  };

  const startHydration = (chain: string): void => {
    addChain(hydratingChains, chain);
  };

  const stopHydration = (chain: string): void => {
    removeChain(hydratingChains, chain);
  };

  const isRefreshing = computed<boolean>(() => get(refreshingChains).size > 0);

  const isHydrating = computed<boolean>(() => get(hydratingChains).size > 0);

  /** Either layer. The read for "is this chain doing anything at all with its balances". */
  const busyChains = computed<Set<string>>(() => new Set([...get(refreshingChains), ...get(hydratingChains)]));

  const useIsRefreshing = (chain: MaybeRefOrGetter<string>): ComputedRef<boolean> =>
    computed<boolean>(() => get(refreshingChains).has(toValue(chain)));

  const useIsHydrating = (chain: MaybeRefOrGetter<string>): ComputedRef<boolean> =>
    computed<boolean>(() => get(hydratingChains).has(toValue(chain)));

  const settleFirstLoad = (): void => {
    set(firstLoadSettled, true);
  };

  const reset = (): void => {
    appliedNetworkResults.clear();
    set(refreshingChains, new Set());
    set(hydratingChains, new Set());
    set(firstLoadSettled, false);
  };

  return {
    busyChains,
    firstLoadSettled,
    hydratingChains,
    isHydrating,
    isRefreshing,
    markNetworkResultApplied,
    networkResultCount,
    refreshingChains,
    reset,
    settleFirstLoad,
    start,
    startHydration,
    stop,
    stopHydration,
    useIsHydrating,
    useIsRefreshing,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalanceRefreshState, import.meta.hot));

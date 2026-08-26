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
 */
export const useBalanceRefreshState = defineStore('balances/refresh-state', () => {
  const refreshingChains = ref<Set<string>>(new Set());
  const hydratingChains = ref<Set<string>>(new Set());

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

  const reset = (): void => {
    set(refreshingChains, new Set());
    set(hydratingChains, new Set());
  };

  return {
    busyChains,
    hydratingChains,
    isHydrating,
    isRefreshing,
    refreshingChains,
    reset,
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

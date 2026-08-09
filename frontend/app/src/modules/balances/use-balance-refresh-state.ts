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
 * Which chains have balance work in flight, split by the two layers that produce it.
 *
 * ⭐ `refreshingChains` is the *network* query — the work a user watches, cancels and retries.
 * `hydratingChains` is the data refresh from the user's own database. They are tracked apart
 * because they mean different things to the UI: a refresh spinner on a row belongs to the former,
 * while "there is nothing to show yet" belongs to both.
 *
 * ⭐ Hydration's liveness lives here rather than in the orchestrator because hydration is not an
 * activity: it has no task-centre row, no cancel and no progress. This store is what every spinner
 * that used to read `useIsActive(BLOCKCHAIN_BALANCES)` for the cached phase now reads instead.
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

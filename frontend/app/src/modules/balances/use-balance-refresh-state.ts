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
  const refreshCounts = new Map<string, number>();
  const chainQueues = new Map<string, Promise<void>>();
  const pendingAccounts = ref<Record<string, Record<string, { address: string; revision: number }>>>({});
  const networkGenerations = new Map<string, number>();
  const appliedNetworks = new Map<string, number>();

  const appliedNetwork = (chain: string): number => appliedNetworks.get(chain) ?? 0;
  const markNetworkApplied = (chain: string): void => {
    appliedNetworks.set(chain, appliedNetwork(chain) + 1);
  };

  const networkGeneration = (chain: string): number => networkGenerations.get(chain) ?? 0;
  const beginNetwork = (chain: string): number => {
    const generation = networkGeneration(chain) + 1;
    networkGenerations.set(chain, generation);
    return generation;
  };

  const markPending = (chain: string, address: string, revision: number): void => {
    const pending = get(pendingAccounts);
    set(pendingAccounts, {
      ...pending,
      [chain]: { ...pending[chain], [address.toLowerCase()]: { address, revision } },
    });
  };

  /** Settle only addresses covered by an applied network response, at or before its revision. */
  const settlePending = (chain: string, revision: number, addresses: string[]): void => {
    const pending = get(pendingAccounts);
    const targeted = new Set(addresses.map(address => address.toLowerCase()));
    const remaining = Object.fromEntries(
      Object.entries(pending[chain] ?? {}).filter(([address, entry]) =>
        entry.revision > revision || !targeted.has(address)),
    );
    set(pendingAccounts, { ...pending, [chain]: remaining });
  };

  const isPending = (chain: string, address: string): boolean =>
    get(pendingAccounts)[chain]?.[address.toLowerCase()] !== undefined;

  const pendingAddresses = (chain: string): string[] =>
    Object.values(get(pendingAccounts)[chain] ?? {}).map(entry => entry.address);

  const refreshCount = (chain: string): number => refreshCounts.get(chain) ?? 0;

  const start = (chain: string): void => {
    refreshCounts.set(chain, refreshCount(chain) + 1);
    addChain(refreshingChains, chain);
  };

  const stop = (chain: string): void => {
    const count = refreshCount(chain);
    if (count <= 1) {
      refreshCounts.delete(chain);
      removeChain(refreshingChains, chain);
    }
    else {
      refreshCounts.set(chain, count - 1);
    }
  };

  const enqueue = async (chain: string, work: () => Promise<void>): Promise<void> => {
    const previous = chainQueues.get(chain) ?? Promise.resolve();
    let release!: () => void;
    const current = new Promise<void>((resolve) => {
      release = resolve;
    });
    chainQueues.set(chain, current);
    start(chain);
    try {
      await previous;
      await work();
    }
    finally {
      if (chainQueues.get(chain) === current)
        chainQueues.delete(chain);
      release();
      stop(chain);
    }
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
    refreshCounts.clear();
    networkGenerations.clear();
    appliedNetworks.clear();
    chainQueues.clear();
    set(pendingAccounts, {});
    set(refreshingChains, new Set());
    set(hydratingChains, new Set());
    set(firstLoadSettled, false);
  };

  return {
    appliedNetwork,
    beginNetwork,
    busyChains,
    enqueue,
    firstLoadSettled,
    hydratingChains,
    isHydrating,
    isPending,
    isRefreshing,
    markNetworkApplied,
    markPending,
    networkGeneration,
    pendingAddresses,
    pendingAccounts,
    refreshingChains,
    reset,
    settleFirstLoad,
    settlePending,
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

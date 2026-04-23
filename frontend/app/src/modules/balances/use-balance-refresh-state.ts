import type { ComputedRef, MaybeRefOrGetter } from 'vue';

export const useBalanceRefreshState = defineStore('balances/refresh-state', () => {
  const refreshingChains = ref<Set<string>>(new Set());

  const start = (chain: string): void => {
    const current = get(refreshingChains);
    if (current.has(chain))
      return;
    const next = new Set(current);
    next.add(chain);
    set(refreshingChains, next);
  };

  const stop = (chain: string): void => {
    const current = get(refreshingChains);
    if (!current.has(chain))
      return;
    const next = new Set(current);
    next.delete(chain);
    set(refreshingChains, next);
  };

  const isRefreshing = computed<boolean>(() => get(refreshingChains).size > 0);

  const useIsRefreshing = (chain: MaybeRefOrGetter<string>): ComputedRef<boolean> =>
    computed<boolean>(() => get(refreshingChains).has(toValue(chain)));

  const reset = (): void => {
    set(refreshingChains, new Set());
  };

  return { isRefreshing, refreshingChains, reset, start, stop, useIsRefreshing };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useBalanceRefreshState, import.meta.hot));

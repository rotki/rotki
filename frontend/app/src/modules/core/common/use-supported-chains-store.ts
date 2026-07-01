import type { EvmChainEntries, SupportedChains } from '@/modules/core/api/types/chains';

/**
 * State-only store for the supported chains data. Kept as a store (not composable
 * state) so it is registered with `StoreTrackPlugin` and cleared automatically by
 * `resetState()` on logout — no bespoke teardown watcher needed. The API call and
 * all derived views live in the `useSupportedChains` composable that wraps this.
 */
export const useSupportedChainsStore = defineStore('core/supported-chains', () => {
  const supportedChains = shallowRef<SupportedChains>([]);
  const allEvmChains = shallowRef<EvmChainEntries>([]);

  return {
    allEvmChains,
    supportedChains,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useSupportedChainsStore, import.meta.hot));

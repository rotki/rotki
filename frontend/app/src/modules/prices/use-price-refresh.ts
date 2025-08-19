import type { MaybeRef } from '@vueuse/core';
import type { AssetPrices } from '@/types/prices';
import { useAggregatedBalances } from '@/composables/balances/use-aggregated-balances';
import { useStatusUpdater } from '@/composables/status';
import { useCollectionMappingStore } from '@/modules/assets/use-collection-mapping-store';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceTaskManager } from '@/modules/prices/use-price-task-manager';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useBalancePricesStore } from '@/store/balances/prices';
import { Section, Status } from '@/types/status';
import { uniqueStrings } from '@/utils/data';

interface UsePriceRefreshReturn {
  adjustPrices: (prices: MaybeRef<AssetPrices>) => void;
  refreshPrice: (asset: string) => Promise<void>;
  refreshPrices: (ignoreCache?: boolean, selectedAssets?: string[] | null) => Promise<void>;
}

export const usePriceRefresh = createSharedComposable((): UsePriceRefreshReturn => {
  const pendingAssets = ref<string[]>([]);

  const { updatePrices } = useBalancesStore();
  const { prices } = storeToRefs(useBalancePricesStore());
  const { collectionMainAssets } = storeToRefs(useCollectionMappingStore());
  const { missingCustomAssets } = useManualBalanceData();
  const { assets: regularAssets } = useAggregatedBalances();
  const { hasCachedPrice } = usePriceUtils();
  const { cacheEuroCollectionAssets, fetchExchangeRates, fetchPrices } = usePriceTaskManager();
  const { setStatus } = useStatusUpdater(Section.PRICES);

  const assets = computed<string[]>(() => [...get(regularAssets), ...get(collectionMainAssets)]);

  const noPriceAssets = useArrayFilter(assets, asset => !hasCachedPrice(asset));

  const adjustPrices = (prices: MaybeRef<AssetPrices>): void => {
    updatePrices({ ...get(prices) });
  };

  const filterMissingAssets = (assets: string[]): string[] => {
    const missingAssets = get(missingCustomAssets);
    return assets.filter(item => !missingAssets.includes(item));
  };

  const performPriceFetch = async (
    ignoreCache: boolean,
    selectedAssets: string[],
  ): Promise<void> => {
    try {
      setStatus(Status.LOADING);
      await cacheEuroCollectionAssets();

      if (ignoreCache) {
        await fetchExchangeRates();
      }

      await fetchPrices({
        ignoreCache,
        selectedAssets: filterMissingAssets(selectedAssets),
      });

      adjustPrices(get(prices));
    }
    finally {
      setStatus(Status.LOADED);
    }
  };

  const refreshPrices = async (ignoreCache = false, selectedAssets: string[] | null = null): Promise<void> => {
    await performPriceFetch(ignoreCache, selectedAssets?.filter(uniqueStrings) ?? get(assets));
  };

  const refreshPrice = async (asset: string): Promise<void> => {
    await performPriceFetch(true, [asset]);
  };

  async function fetchNoPriceAssets(assets: string[]): Promise<void> {
    const pending = get(pendingAssets);
    const newAssets = assets.filter(asset => !pending.includes(asset));

    if (newAssets.length === 0)
      return;

    pending.push(...newAssets);
    set(pendingAssets, pending);
    try {
      await refreshPrices(false, newAssets);
    }
    finally {
      const currentPending = get(pendingAssets);
      const filteredPending = currentPending.filter(asset => !newAssets.includes(asset));
      set(pendingAssets, filteredPending);
    }
  }

  // Watch for assets without prices and automatically fetch them
  watchDebounced(noPriceAssets, async assets => fetchNoPriceAssets(assets), { debounce: 800, maxWait: 2000 });

  return {
    adjustPrices,
    refreshPrice,
    refreshPrices,
  };
});

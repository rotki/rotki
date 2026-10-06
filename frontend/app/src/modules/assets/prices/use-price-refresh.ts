import type { ComputedRef, MaybeRef } from 'vue';
import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useCollectionMappingStore } from '@/modules/assets/use-collection-mapping-store';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UsePriceRefreshReturn {
  adjustPrices: (prices: MaybeRef<AssetPrices>) => void;
  refreshPrice: (asset: string) => Promise<void>;
  refreshPrices: (ignoreCache?: boolean, selectedAssets?: string[] | null) => Promise<void>;
  /**
   * Whether a refresh of current prices is running: the exchange rates or the latest prices.
   *
   * @remarks
   * Not the whole PRICES kind. Historic and daily lookups, the oracle cache and manual price edits
   * are PRICES work too, and reading the kind let a single historic lookup disable every refresh
   * button and put every price row in loading.
   */
  refreshing: ComputedRef<boolean>;
}

export const usePriceRefresh = createSharedComposable((): UsePriceRefreshReturn => {
  const pendingAssets = ref<string[]>([]);

  const { updatePrices } = useBalancesStore();
  const { prices } = storeToRefs(useBalancePricesStore());
  const { collectionMainAssets } = storeToRefs(useCollectionMappingStore());
  const { missingCustomAssets } = useManualBalanceData();
  const { assets: regularAssets } = useAggregatedBalances();
  const { hasCachedPrice } = usePriceUtils();
  const { refreshLatestPrices } = usePriceTaskManager();
  const { useIsActive, useIsActivePrefix } = useTaskCenter();

  const refreshing = logicOr(
    useIsActive(ActivityKind.PRICES, ActivityPart.EXCHANGE_RATES),
    useIsActivePrefix(ActivityKind.PRICES, ActivityPart.LATEST),
  );

  const assets = computed<string[]>(() => [...get(regularAssets), ...get(collectionMainAssets)]);

  const noPriceAssets = useArrayFilter(assets, asset => !hasCachedPrice(asset));

  const adjustPrices = (prices: MaybeRef<AssetPrices>): void => {
    updatePrices({ ...get(prices) });
  };

  const filterMissingAssets = (assets: string[]): string[] => {
    const missingAssets = get(missingCustomAssets);
    return assets.filter(item => !missingAssets.includes(item));
  };

  /**
   * Fetches prices for the given assets and writes the result into the balances store, one
   * refresh at a time; see `refreshLatestPrices`.
   *
   * @remarks
   * Sets no status of its own: the in-flight state belongs to its PRICES activity, read through
   * {@link UsePriceRefreshReturn.refreshing}. Custom assets that no longer resolve are dropped
   * before the request rather than sent and failed.
   *
   * @param ignoreCache - bypasses the cached prices, and additionally re-fetches exchange rates.
   * @param selectedAssets - the assets to price.
   */
  const runRefresh = async (ignoreCache: boolean, selectedAssets: string[]): Promise<void> => {
    const applyPrices = (): void => adjustPrices(get(prices));
    const assetsToPrice = filterMissingAssets(selectedAssets);
    if (assetsToPrice.length === 0 && !ignoreCache) {
      applyPrices();
      return;
    }

    await refreshLatestPrices({ ignoreCache, selectedAssets: assetsToPrice }, applyPrices);
  };

  const refreshPrices = async (ignoreCache = false, selectedAssets: string[] | null = null): Promise<void> => {
    const assetsToRefresh = selectedAssets?.filter(uniqueStrings)
      ?? [...get(assets), ...Object.keys(get(prices))].filter(uniqueStrings);
    await runRefresh(ignoreCache, assetsToRefresh);
  };

  const refreshPrice = async (asset: string): Promise<void> => {
    await runRefresh(true, [asset]);
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

  watchDebounced(noPriceAssets, async assets => fetchNoPriceAssets(assets), { debounce: 800, maxWait: 2000 });

  return {
    adjustPrices,
    refreshing,
    refreshPrice,
    refreshPrices,
  };
});

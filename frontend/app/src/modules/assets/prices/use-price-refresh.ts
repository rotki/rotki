import type { MaybeRef } from 'vue';
import type { AssetPrices } from '@/modules/assets/prices/price-types';
import { startPromise } from '@shared/utils';
import { usePriceTaskManager } from '@/modules/assets/prices/use-price-task-manager';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { useCollectionMappingStore } from '@/modules/assets/use-collection-mapping-store';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useAggregatedBalances } from '@/modules/balances/use-aggregated-balances';
import { useBalancePricesStore } from '@/modules/balances/use-balance-prices-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { uniqueStrings } from '@/modules/core/common/data/data';

interface PriceRefreshTask {
  ignoreCache: boolean;
  selectedAssets: string[];
  resolve: () => void;
  reject: (error: any) => void;
}

interface UsePriceRefreshReturn {
  adjustPrices: (prices: MaybeRef<AssetPrices>) => void;
  refreshPrice: (asset: string) => Promise<void>;
  refreshPrices: (ignoreCache?: boolean, selectedAssets?: string[] | null) => Promise<void>;
}

export const usePriceRefresh = createSharedComposable((): UsePriceRefreshReturn => {
  const pendingAssets = ref<string[]>([]);
  const taskQueue = ref<PriceRefreshTask[]>([]);
  const isProcessingQueue = ref<boolean>(false);

  const { updatePrices } = useBalancesStore();
  const { prices } = storeToRefs(useBalancePricesStore());
  const { collectionMainAssets } = storeToRefs(useCollectionMappingStore());
  const { missingCustomAssets } = useManualBalanceData();
  const { assets: regularAssets } = useAggregatedBalances();
  const { hasCachedPrice } = usePriceUtils();
  const { fetchExchangeRates, fetchPrices } = usePriceTaskManager();

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
   * Fetches prices for the given assets and writes the result into the balances store.
   *
   * @remarks
   * Sets no status of its own: the in-flight state belongs to the native PRICES activity, read
   * with `useTaskCenter().useWorkStatus(ActivityKind.PRICES)`. Custom assets that no longer
   * resolve are dropped before the request rather than sent and failed.
   *
   * @param ignoreCache - bypasses the cached prices, and additionally re-fetches exchange rates.
   * @param selectedAssets - the assets to price; an empty list requests none.
   */
  const performPriceFetch = async (
    ignoreCache: boolean,
    selectedAssets: string[],
  ): Promise<void> => {
    if (ignoreCache) {
      await fetchExchangeRates();
    }

    await fetchPrices({
      ignoreCache,
      selectedAssets: filterMissingAssets(selectedAssets),
    });

    adjustPrices(get(prices));
  };

  const processQueue = async (): Promise<void> => {
    if (get(isProcessingQueue)) {
      return;
    }

    set(isProcessingQueue, true);

    try {
      while (get(taskQueue).length > 0) {
        const task = get(taskQueue).shift();
        if (!task)
          break;

        try {
          await performPriceFetch(task.ignoreCache, task.selectedAssets);
          task.resolve();
        }
        catch (error) {
          task.reject(error);
        }
      }
    }
    finally {
      set(isProcessingQueue, false);
    }
  };

  /**
   * Queues one price fetch and resolves once that fetch, and not merely the queueing, has run.
   *
   * @remarks
   * Fetches are serialised: only one drain of the queue runs at a time, so two overlapping
   * refreshes cannot both hit the backend and race each other's write into the balances store.
   * The drain is started on the next tick, so several calls made in the same tick are picked up
   * by one pass of the loop. Each queued task keeps its own settlers, so a failure reaches the
   * caller that enqueued it rather than whichever caller happened to trigger the drain.
   *
   * @param ignoreCache - forwarded to the fetch; bypasses cached prices and exchange rates.
   * @param selectedAssets - the assets to price.
   */
  const enqueueTask = async (ignoreCache: boolean, selectedAssets: string[]): Promise<void> =>
    new Promise<void>((resolve, reject) => {
      const task: PriceRefreshTask = {
        ignoreCache,
        reject,
        resolve,
        selectedAssets,
      };

      get(taskQueue).push(task);

      startPromise(nextTick(() => {
        startPromise(processQueue());
      }));
    });

  const refreshPrices = async (ignoreCache = false, selectedAssets: string[] | null = null): Promise<void> => {
    const assetsToRefresh = selectedAssets?.filter(uniqueStrings)
      ?? [...get(assets), ...Object.keys(get(prices))].filter(uniqueStrings);
    await enqueueTask(ignoreCache, assetsToRefresh);
  };

  const refreshPrice = async (asset: string): Promise<void> => {
    await enqueueTask(true, [asset]);
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
    refreshPrice,
    refreshPrices,
  };
});

import type { ComputedRef, Ref } from 'vue';
import type { TaskMeta } from '@/modules/core/tasks/types';
import {
  type BigNumber,
  type CommonQueryStatusData,
  type FailedHistoricalAssetPriceResponse,
  NoPrice,
} from '@rotki/common';
import { HistoricPrices } from '@/modules/assets/prices/price-types';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceApi } from '@/modules/balances/api/use-price-api';
import { createItemCache } from '@/modules/core/common/use-item-cache';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';

interface UseHistoricPriceCacheReturn {
  cache: ReturnType<typeof createItemCache<BigNumber>>['cache'];
  createKey: (fromAsset: string, timestamp: number | string) => string;
  failedDailyPrices: Ref<Record<string, FailedHistoricalAssetPriceResponse>>;
  getHistoricPrice: (fromAsset: string, timestamp: number) => BigNumber;
  getIsPending: (identifier: string) => boolean;
  historicalDailyPriceStatus: Ref<CommonQueryStatusData | undefined>;
  historicPriceInCurrentCurrency: (fromAsset: string, timestamp: number) => ComputedRef<BigNumber>;
  isPending: ReturnType<typeof createItemCache<BigNumber>>['isPending'];
  resolvedFailedDailyPrices: Ref<Record<string, number[]>>;
  reset: () => void;
  resetHistoricalPricesData: (items: { fromAsset: string; timestamp: number }[]) => void;
  resolve: (key: string) => BigNumber | null;
  unknown: Map<string, number>;
}

export const useHistoricPriceCache = createSharedComposable((): UseHistoricPriceCacheReturn => {
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { failedDailyPrices, historicalDailyPriceStatus, resolvedFailedDailyPrices } = storeToRefs(useHistoricCachePriceStore());
  const { queryHistoricalRates } = usePriceApi();
  const { cancelTaskByTaskType, runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

  const createKey = (fromAsset: string, timestamp: number | string): string => `${fromAsset}#${timestamp}`;

  async function fetchHistoricPrices(keys: string[]): ReturnType<Parameters<typeof createItemCache<BigNumber>>[0]> {
    const taskType = TaskType.FETCH_HISTORIC_PRICE;
    const assetsTimestamp = keys.map((key) => {
      const [from, timestamp] = key.split('#');

      return [from, timestamp];
    });
    const targetAsset = get(currencySymbol);

    let data: HistoricPrices = { assets: {}, targetAsset: '' };

    const outcome = await runTask<HistoricPrices, TaskMeta>(
      async () => queryHistoricalRates({
        assetsTimestamp,
        targetAsset,
      }),
      {
        type: taskType,
        meta: {
          description: t(
            'actions.balances.historic_fetch_price.task.description',
            {
              count: assetsTimestamp.length,
              toAsset: targetAsset,
            },
            2,
          ),
          title: t('actions.balances.historic_fetch_price.task.title'),
        },
        unique: false,
      },
    );

    if (outcome.success) {
      data = outcome.result;
    }
    else if (isActionableFailure(outcome)) {
      notifyError(
        t('actions.balances.historic_fetch_price.task.title'),
        t('actions.balances.historic_fetch_price.error.message', {
          message: outcome.message,
        }),
      );
    }

    const response = HistoricPrices.parse(data);

    return function* (): Generator<{ key: string; item: BigNumber }, void> {
      for (const assetTimestamp of assetsTimestamp) {
        const [fromAsset, timestamp] = assetTimestamp;
        const key = createKey(fromAsset, timestamp);

        const item = response.assets?.[fromAsset]?.[timestamp];
        yield { item, key };
      }
    };
  }

  const {
    cache,
    deleteCacheKey,
    getIsPending,
    isPending,
    reset,
    resolve,
    unknown,
  } = createItemCache<BigNumber>(async keys => fetchHistoricPrices(keys));

  function getHistoricPrice(fromAsset: string, timestamp: number): BigNumber {
    const key = createKey(fromAsset, timestamp);

    if (getIsPending(key))
      return NoPrice;

    return resolve(key) || NoPrice;
  }

  function historicPriceInCurrentCurrency(fromAsset: string, timestamp: number): ComputedRef<BigNumber> {
    return computed<BigNumber>(() => getHistoricPrice(fromAsset, timestamp));
  }

  function resetHistoricalPricesData(items: { fromAsset: string; timestamp: number }[]): void {
    const oneHourInMs = 60 * 60;
    const keysToBeDeleted = new Set<string>();
    const cacheKeys = Object.keys(get(cache));
    const unknownKeys = unknown.keys();

    items.forEach((item) => {
      const targetTime = item.timestamp;
      const fromAsset = item.fromAsset;
      const lowerBound = targetTime - oneHourInMs;
      const upperBound = targetTime + oneHourInMs;

      // Do deletion for (timestamp - 1 hour) and (timestamp + 1 hour)
      [...cacheKeys, ...unknownKeys].forEach((cacheKey) => {
        const [cacheAsset, cacheTimestamp] = cacheKey.split('#');
        const cacheTime = parseInt(cacheTimestamp, 10);

        if (cacheAsset === fromAsset && cacheTime >= lowerBound && cacheTime <= upperBound)
          keysToBeDeleted.add(cacheKey);
      });
    });

    keysToBeDeleted.forEach((key) => {
      deleteCacheKey(key);
    });
  }

  watch(currencySymbol, async () => {
    await cancelTaskByTaskType([TaskType.FETCH_HISTORIC_PRICE, TaskType.FETCH_DAILY_HISTORIC_PRICE]);
    set(failedDailyPrices, {});
    set(resolvedFailedDailyPrices, {});
    reset();
  });

  return {
    cache,
    createKey,
    failedDailyPrices,
    getHistoricPrice,
    getIsPending,
    historicalDailyPriceStatus,
    historicPriceInCurrentCurrency,
    isPending,
    resolvedFailedDailyPrices,
    reset,
    resetHistoricalPricesData,
    resolve,
    unknown,
  };
});

import { HistoricPrices } from '@/types/prices';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { useTaskStore } from '@/store/tasks';
import { useNotificationsStore } from '@/store/notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { usePriceApi } from '@/composables/api/balances/price';
import { useItemCache } from '@/composables/item-cache';
import type { BigNumber } from '@rotki/common';
import type { TaskMeta } from '@/types/task';

export const useHistoricCachePriceStore = defineStore('prices/historic-cache', () => {
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { queryHistoricalRates } = usePriceApi();
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { notify } = useNotificationsStore();

  const createKey = (fromAsset: string, timestamp: number | string): string => `${fromAsset}#${timestamp}`;

  const fetchHistoricPrices = async (keys: string[]) => {
    const taskType = TaskType.FETCH_HISTORIC_PRICE;
    const assetsTimestamp = keys.map((key) => {
      const [from, timestamp] = key.split('#');

      return [from, timestamp];
    });
    const targetAsset = get(currencySymbol);

    const { taskId } = await queryHistoricalRates({
      assetsTimestamp,
      targetAsset,
    });

    let data = { assets: {}, targetAsset: '' };

    try {
      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
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
        true,
      );
      data = result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.balances.historic_fetch_price.error.message', {
            message: error.message,
          }),
          title: t('actions.balances.historic_fetch_price.task.title'),
        });
      }
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
  };

  const { cache, deleteCacheKey, isPending, reset, retrieve } = useItemCache<BigNumber>(async keys =>
    fetchHistoricPrices(keys),
  );

  const historicPriceInCurrentCurrency = (fromAsset: string, timestamp: number): ComputedRef<BigNumber> =>
    computed(() => {
      const key = createKey(fromAsset, timestamp);

      if (get(isPending(key)))
        return NoPrice;

      return get(retrieve(key)) || NoPrice;
    });

  const resetHistoricalPricesData = (items: { fromAsset: string; timestamp: number }[]): void => {
    const oneHourInMs = 60 * 60;
    const keysToBeDeleted = new Set<string>();
    const cacheKeys = Object.keys(get(cache));

    items.forEach((item) => {
      const targetTime = item.timestamp;
      const lowerBound = targetTime - oneHourInMs;
      const upperBound = targetTime + oneHourInMs;

      // Do deletion for (timestamp - 1 hour) and (timestamp + 1 hour)
      cacheKeys.forEach((cacheKey) => {
        const [cacheAsset, cacheTimestamp] = cacheKey.split('#');
        const cacheTime = parseInt(cacheTimestamp, 10);

        if (cacheAsset === item.fromAsset && cacheTime >= lowerBound && cacheTime <= upperBound)
          keysToBeDeleted.add(cacheKey);
      });
    });

    keysToBeDeleted.forEach((key) => {
      deleteCacheKey(key);
    });
  };

  watch(currencySymbol, () => {
    reset();
  });

  return {
    cache,
    createKey,
    historicPriceInCurrentCurrency,
    isPending,
    reset,
    resetHistoricalPricesData,
    retrieve,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricCachePriceStore, import.meta.hot));

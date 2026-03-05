import type { StatsPriceQueryData } from '@/modules/messaging/types';
import type { TaskMeta } from '@/types/task';
import { type BigNumber, type CommonQueryStatusData, type FailedHistoricalAssetPriceResponse, NoPrice } from '@rotki/common';
import { usePriceApi } from '@/composables/api/balances/price';
import { createItemCache } from '@/composables/item-cache';
import { getErrorMessage, useNotifications } from '@/modules/notifications/use-notifications';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useTaskStore } from '@/store/tasks';
import { HistoricPrices } from '@/types/prices';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';

export const useHistoricCachePriceStore = defineStore('prices/historic-cache', () => {
  const statsPriceQueryStatus = shallowRef<Record<string, StatsPriceQueryData>>({});
  const historicalPriceStatus = shallowRef<CommonQueryStatusData>();
  const historicalDailyPriceStatus = shallowRef<CommonQueryStatusData>();
  const failedDailyPrices = shallowRef<Record<string, FailedHistoricalAssetPriceResponse>>({});
  const resolvedFailedDailyPrices = shallowRef<Record<string, number[]>>({});

  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { queryHistoricalRates } = usePriceApi();
  const { awaitTask, cancelTaskByTaskType } = useTaskStore();
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();

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
    catch (error: unknown) {
      if (!isTaskCancelled(error)) {
        notifyError(
          t('actions.balances.historic_fetch_price.task.title'),
          t('actions.balances.historic_fetch_price.error.message', {
            message: getErrorMessage(error),
          }),
        );
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

  const { cache, deleteCacheKey, getIsPending, isPending, reset, resolve, unknown } = createItemCache<BigNumber>(async keys =>
    fetchHistoricPrices(keys),
  );

  function getHistoricPrice(fromAsset: string, timestamp: number): BigNumber {
    const key = createKey(fromAsset, timestamp);

    if (getIsPending(key))
      return NoPrice;

    return resolve(key) || NoPrice;
  }

  const historicPriceInCurrentCurrency = (fromAsset: string, timestamp: number): ComputedRef<BigNumber> =>
    computed<BigNumber>(() => getHistoricPrice(fromAsset, timestamp));

  const resetHistoricalPricesData = (items: { fromAsset: string; timestamp: number }[]): void => {
    const oneHourInMs = 60 * 60;
    const keysToBeDeleted = new Set<string>();
    const cacheKeys = Object.keys(get(cache));
    const unknownKeys = get(unknown).keys();

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
  };

  watch(currencySymbol, async () => {
    await cancelTaskByTaskType([TaskType.FETCH_HISTORIC_PRICE, TaskType.FETCH_DAILY_HISTORIC_PRICE]);
    set(failedDailyPrices, {});
    set(resolvedFailedDailyPrices, {});
    reset();
  });

  const getProtocolStatsPriceQueryStatus = (counterparty: string): ComputedRef<StatsPriceQueryData | undefined> => computed(() => get(statsPriceQueryStatus)[counterparty]);

  const setStatsPriceQueryStatus = (data: StatsPriceQueryData): void => {
    const currentData = {
      ...get(statsPriceQueryStatus),
    };

    currentData[data.counterparty] = data;

    set(statsPriceQueryStatus, currentData);
  };

  const resetProtocolStatsPriceQueryStatus = (counterparty: string): void => {
    const currentData = {
      ...get(statsPriceQueryStatus),
    };

    delete currentData[counterparty];

    set(statsPriceQueryStatus, currentData);
  };

  const setHistoricalDailyPriceStatus = (status: CommonQueryStatusData): void => {
    set(historicalDailyPriceStatus, status);
  };

  const setHistoricalPriceStatus = (status: CommonQueryStatusData): void => {
    set(historicalPriceStatus, status);
  };

  return {
    cache,
    createKey,
    failedDailyPrices,
    getHistoricPrice,
    getIsPending,
    getProtocolStatsPriceQueryStatus,
    historicalDailyPriceStatus,
    historicalPriceStatus,
    historicPriceInCurrentCurrency,
    isPending,
    reset,
    resetHistoricalPricesData,
    resetProtocolStatsPriceQueryStatus,
    resolvedFailedDailyPrices,
    resolve,
    setHistoricalDailyPriceStatus,
    setHistoricalPriceStatus,
    setStatsPriceQueryStatus,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricCachePriceStore, import.meta.hot));

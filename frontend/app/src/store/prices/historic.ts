import { HistoricPrices } from '@/types/prices';
import { TaskType } from '@/types/task-type';
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

    let data = { targetAsset: '', assets: {} };

    try {
      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.balances.historic_fetch_price.task.title'),
          description: t(
            'actions.balances.historic_fetch_price.task.description',
            {
              count: assetsTimestamp.length,
              toAsset: targetAsset,
            },
            2,
          ),
        },
        true,
      );
      data = result;
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        notify({
          title: t('actions.balances.historic_fetch_price.task.title'),
          message: t('actions.balances.historic_fetch_price.error.message', {
            message: error.message,
          }),
          display: true,
        });
      }
    }

    const response = HistoricPrices.parse(data);

    return function* (): Generator<{ key: string; item: BigNumber }, void> {
      for (const assetTimestamp of assetsTimestamp) {
        const [fromAsset, timestamp] = assetTimestamp;
        const key = createKey(fromAsset, timestamp);

        const item = response.assets?.[fromAsset]?.[timestamp];
        yield { key, item };
      }
    };
  };

  const { cache, isPending, retrieve, reset, deleteCacheKey } = useItemCache<BigNumber>(keys =>
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
    items.forEach((item) => {
      const key = createKey(item.fromAsset, item.timestamp);
      deleteCacheKey(key);
    });
  };

  watch(currencySymbol, () => {
    reset();
  });

  return {
    cache,
    isPending,
    retrieve,
    reset,
    createKey,
    historicPriceInCurrentCurrency,
    resetHistoricalPricesData,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useHistoricCachePriceStore, import.meta.hot));

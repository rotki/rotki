import { type BigNumber } from '@rotki/common';
import { type ComputedRef } from 'vue';
import { HistoricPrices } from '@/types/prices';
import { TaskType } from '@/types/task-type';
import { type TaskMeta } from '@/types/task';
import { NoPrice } from '@/utils/bignumbers';

export const useHistoricCachePriceStore = defineStore(
  'prices/historic-cache',
  () => {
    const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
    const { queryHistoricalRates } = usePriceApi();
    const { awaitTask } = useTaskStore();
    const { t, tc } = useI18n();

    const fetchHistoricPrices = async (keys: string[]) => {
      const taskType = TaskType.FETCH_HISTORIC_PRICE;
      const assetsTimestamp = keys.map(key => key.split('#'));
      const targetAsset = get(currencySymbol);

      const { taskId } = await queryHistoricalRates({
        assetsTimestamp,
        targetAsset
      });

      const { result } = await awaitTask<HistoricPrices, TaskMeta>(
        taskId,
        taskType,
        {
          title: t(
            'actions.balances.historic_fetch_price.task.title'
          ).toString(),
          description: tc(
            'actions.balances.historic_fetch_price.task.description',
            2,
            {
              count: assetsTimestamp.length,
              toAsset: targetAsset
            }
          )
        },
        true
      );

      const response = HistoricPrices.parse(result);

      return function* () {
        for (const assetTimestamp of assetsTimestamp) {
          const [fromAsset, timestamp] = assetTimestamp;
          const key = `${fromAsset}#${timestamp}`;

          const item = response.assets?.[fromAsset]?.[timestamp];
          yield { key, item };
        }
      };
    };

    const historicPriceInCurrentCurrency = (
      fromAsset: string,
      timestamp: number
    ): ComputedRef<BigNumber> =>
      computed(() => {
        const key = `${fromAsset}#${timestamp}`;

        if (get(isPending(key))) {
          return NoPrice;
        }

        return get(retrieve(key)) || NoPrice;
      });

    const { cache, isPending, retrieve, reset } = useItemCache<BigNumber>(
      keys => fetchHistoricPrices(keys)
    );

    watch(currencySymbol, () => {
      reset();
    });

    return {
      cache,
      isPending,
      retrieve,
      reset,
      historicPriceInCurrentCurrency
    };
  }
);

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useHistoricCachePriceStore, import.meta.hot)
  );
}

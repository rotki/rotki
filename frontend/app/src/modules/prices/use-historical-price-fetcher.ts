import type { TaskMeta } from '@/types/task';
import { type HistoricalAssetPricePayload, HistoricalAssetPriceResponse } from '@rotki/common';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useNotificationsStore } from '@/store/notifications';
import { useHistoricCachePriceStore } from '@/store/prices/historic';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';

interface UseHistoricalPriceFetcherReturn {
  fetchHistoricalAssetPrice: (payload: HistoricalAssetPricePayload) => Promise<HistoricalAssetPriceResponse>;
}

export function useHistoricalPriceFetcher(): UseHistoricalPriceFetcherReturn {
  const { t } = useI18n({ useScope: 'global' });

  const api = useStatisticsApi();
  const { awaitTask } = useTaskStore();
  const { assetName } = useAssetInfoRetrieval();
  const { notify } = useNotificationsStore();
  const { failedDailyPrices, resolvedFailedDailyPrices } = storeToRefs(useHistoricCachePriceStore());

  const resetFailedStates = (asset: string, parsed: HistoricalAssetPriceResponse, excludeTimestamps: number[]): void => {
    const { noPricesTimestamps, rateLimitedPricesTimestamps } = parsed;

    const failedState = { ...get(failedDailyPrices) };
    const resolvedState = { ...get(resolvedFailedDailyPrices) };

    if ((noPricesTimestamps.length === 0 && excludeTimestamps.length === 0) && rateLimitedPricesTimestamps.length === 0) {
      if (failedState[asset]) {
        const updatedFailedPrices = { ...failedState };
        delete updatedFailedPrices[asset];
        set(failedDailyPrices, updatedFailedPrices);
      }
      if (resolvedState[asset]) {
        delete resolvedState[asset];
        set(resolvedFailedDailyPrices, resolvedState);
      }
    }
    else {
      set(failedDailyPrices, {
        ...failedState,
        [asset]: {
          noPricesTimestamps: noPricesTimestamps.length > 0 ? noPricesTimestamps : excludeTimestamps,
          rateLimitedPricesTimestamps,
        },
      });
    }
  };

  const fetchHistoricalAssetPrice = async (payload: HistoricalAssetPricePayload): Promise<HistoricalAssetPriceResponse> => {
    try {
      const asset = payload.asset;
      const failedState = { ...get(failedDailyPrices) };
      const resolvedState = { ...get(resolvedFailedDailyPrices) };
      const failedTimestamps = failedState[asset]?.noPricesTimestamps || [];
      const resolvedTimestamps = resolvedState[asset] || [];

      const excludeTimestamps
        = failedTimestamps.filter(timestamp => !resolvedTimestamps.includes(timestamp));

      const taskType = TaskType.FETCH_DAILY_HISTORIC_PRICE;
      const { taskId } = await api.queryHistoricalAssetPrices({
        ...payload,
        excludeTimestamps,
      });
      const { result } = await awaitTask<HistoricalAssetPriceResponse, TaskMeta>(taskId, taskType, {
        description: t('actions.balances.historic_fetch_price.daily.task.detail', {
          asset: get(assetName(payload.asset)),
        }),
        title: t('actions.balances.historic_fetch_price.daily.task.title'),
      });

      const parsed = HistoricalAssetPriceResponse.parse(result);
      resetFailedStates(asset, parsed, excludeTimestamps);
      return parsed;
    }
    catch (error: any) {
      logger.error(error);
      if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.balances.historic_fetch_price.daily.error.message'),
          title: t('actions.balances.historic_fetch_price.daily.task.title'),
        });
      }

      return {
        noPricesTimestamps: [],
        prices: {},
        rateLimitedPricesTimestamps: [],
      };
    }
  };

  return {
    fetchHistoricalAssetPrice,
  };
}

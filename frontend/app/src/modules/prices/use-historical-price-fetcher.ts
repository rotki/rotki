import type { TaskMeta } from '@/modules/tasks/types';
import { type HistoricalAssetPricePayload, HistoricalAssetPriceResponse } from '@rotki/common';
import { useStatisticsApi } from '@/composables/api/statistics/statistics-api';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { logger } from '@/modules/common/logging/logging';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useHistoricPriceCache } from '@/modules/prices/use-historic-price-cache';
import { TaskType } from '@/modules/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/tasks/use-task-handler';

interface UseHistoricalPriceFetcherReturn {
  fetchHistoricalAssetPrice: (payload: HistoricalAssetPricePayload) => Promise<HistoricalAssetPriceResponse>;
}

export function useHistoricalPriceFetcher(): UseHistoricalPriceFetcherReturn {
  const { t } = useI18n({ useScope: 'global' });

  const api = useStatisticsApi();
  const { runTask } = useTaskHandler();
  const { getAssetField } = useAssetInfoRetrieval();
  const { notifyError } = useNotifications();
  const { failedDailyPrices, resolvedFailedDailyPrices } = useHistoricPriceCache();

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
    const asset = payload.asset;
    const failedState = { ...get(failedDailyPrices) };
    const resolvedState = { ...get(resolvedFailedDailyPrices) };
    const failedTimestamps = failedState[asset]?.noPricesTimestamps || [];
    const resolvedTimestamps = resolvedState[asset] || [];

    const excludeTimestamps
      = failedTimestamps.filter(timestamp => !resolvedTimestamps.includes(timestamp));

    const outcome = await runTask<HistoricalAssetPriceResponse, TaskMeta>(
      async () => api.queryHistoricalAssetPrices({
        ...payload,
        excludeTimestamps,
      }),
      {
        type: TaskType.FETCH_DAILY_HISTORIC_PRICE,
        meta: {
          description: t('actions.balances.historic_fetch_price.daily.task.detail', {
            asset: getAssetField(payload.asset, 'name'),
          }),
          title: t('actions.balances.historic_fetch_price.daily.task.title'),
        },
      },
    );

    if (outcome.success) {
      const parsed = HistoricalAssetPriceResponse.parse(outcome.result);
      resetFailedStates(asset, parsed, excludeTimestamps);
      return parsed;
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      notifyError(
        t('actions.balances.historic_fetch_price.daily.task.title'),
        t('actions.balances.historic_fetch_price.daily.error.message'),
      );
    }

    return {
      noPricesTimestamps: [],
      prices: {},
      rateLimitedPricesTimestamps: [],
    };
  };

  return {
    fetchHistoricalAssetPrice,
  };
}

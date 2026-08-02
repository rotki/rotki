import { type HistoricalAssetPricePayload, HistoricalAssetPriceResponse } from '@rotki/common';
import { getOr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseHistoricalPriceFetcherReturn {
  fetchHistoricalAssetPrice: (payload: HistoricalAssetPricePayload) => Promise<HistoricalAssetPriceResponse>;
}

export function useHistoricalPriceFetcher(): UseHistoricalPriceFetcherReturn {
  const { t } = useI18n({ useScope: 'global' });

  const api = useStatisticsApi();
  const { submitTask } = useNativeTask();
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

    const empty: HistoricalAssetPriceResponse = {
      noPricesTimestamps: [],
      prices: {},
      rateLimitedPricesTimestamps: [],
    };
    // One native PRICES activity per (asset, interval, range) — the payload fields that make the
    // query distinct. A per-asset id alone would let two different ranges for the same asset
    // dedup onto one promise. Readers aggregate with `useWorkStatusPrefix`.
    const outcome = await submitTask<HistoricalAssetPriceResponse>({
      id: makeActivityId(
        ActivityKind.PRICES,
        ActivityPart.DAILY,
        asset,
        payload.interval,
        payload.fromTimestamp,
        payload.toTimestamp,
      ),
      kind: ActivityKind.PRICES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<HistoricalAssetPriceResponse, TaskError>> => mapResult(
        await runTask<HistoricalAssetPriceResponse>(
          async () => api.queryHistoricalAssetPrices({
            ...payload,
            excludeTimestamps,
          }),
        ),
        (result) => {
          const parsed = HistoricalAssetPriceResponse.parse(result);
          resetFailedStates(asset, parsed, excludeTimestamps);
          return parsed;
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.daily'), { asset: getAssetField(payload.asset, 'name') }),
      title: t('task_center.group.prices'),
    });

    onActionableError(outcome, (error) => {
      logger.error(error.message);
      notifyError(
        t('actions.balances.historic_fetch_price.daily.task.title'),
        t('actions.balances.historic_fetch_price.daily.error.message'),
      );
    });

    return getOr(outcome, empty);
  };

  return {
    fetchHistoricalAssetPrice,
  };
}

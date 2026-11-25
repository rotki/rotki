import { type HistoricalAssetPricePayload, HistoricalAssetPriceResponse } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { getOr, map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { dailyPricesActivity } from '@/modules/assets/prices/prices.activity';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { logger } from '@/modules/core/common/logging/logging';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseHistoricalPriceFetcherReturn {
  fetchHistoricalAssetPrice: (payload: HistoricalAssetPricePayload) => Promise<HistoricalAssetPriceResponse>;
}

export function useHistoricalPriceFetcher(): UseHistoricalPriceFetcherReturn {
  const { t } = useI18n({ useScope: 'global' });

  const api = useStatisticsApi();
  const { submitTask } = useNativeTask();
  const { getAssetField } = useAssetInfoRetrieval();
  const { failedDailyPrices, resolvedFailedDailyPrices } = useHistoricPriceCache();
  const priceSeries = usePriceSeriesStore();
  const currencySymbol = useSetting('currencySymbol');

  /**
   * Files what this fetch could not price. Only the timestamps its answer settles (priced, or
   * filed on one of its lists) change; every other one keeps what was filed for it, since this
   * fetch says nothing about it: the backfill files the days it gave up on at their day start,
   * and the excluded timestamps were not asked about.
   *
   * A cache-only read says nothing about the oracles, so it only takes the timestamps it found a
   * price for off the lists and files nothing.
   */
  const resetFailedStates = (payload: HistoricalAssetPricePayload, parsed: HistoricalAssetPriceResponse): void => {
    const asset = payload.asset;
    const failedState = { ...get(failedDailyPrices) };
    const resolvedState = { ...get(resolvedFailedDailyPrices) };
    const previous = failedState[asset];
    const cacheOnly = payload.onlyCachePeriod !== undefined;
    const settled = new Set([
      ...Object.keys(parsed.prices).map(Number),
      ...(cacheOnly ? [] : [...parsed.failedPricesTimestamps, ...parsed.noPricesTimestamps, ...parsed.rateLimitedPricesTimestamps]),
    ]);
    const merge = (kept: number[] | undefined, fetched: number[]): number[] => [...new Set([
      ...(kept ?? []).filter(time => !settled.has(time)),
      ...(cacheOnly ? [] : fetched),
    ])];

    const failedPricesTimestamps = merge(previous?.failedPricesTimestamps, parsed.failedPricesTimestamps);
    const noPricesTimestamps = merge(previous?.noPricesTimestamps, parsed.noPricesTimestamps);
    const rateLimitedPricesTimestamps = merge(previous?.rateLimitedPricesTimestamps, parsed.rateLimitedPricesTimestamps);

    if (noPricesTimestamps.length === 0 && rateLimitedPricesTimestamps.length === 0 && failedPricesTimestamps.length === 0) {
      if (failedState[asset]) {
        delete failedState[asset];
        set(failedDailyPrices, failedState);
      }
      if (resolvedState[asset]) {
        delete resolvedState[asset];
        set(resolvedFailedDailyPrices, resolvedState);
      }
    }
    else {
      set(failedDailyPrices, {
        ...failedState,
        [asset]: { failedPricesTimestamps, noPricesTimestamps, rateLimitedPricesTimestamps },
      });
    }
  };

  /**
   * Hands the prices this fetch found to the graphs, which would otherwise not read a day the
   * backfill gave up on again. Prices are in the main currency, so an answer that arrives after a
   * switch is left out.
   */
  const publishPrices = (asset: string, parsed: HistoricalAssetPriceResponse, currency: string): void => {
    if (get(currencySymbol) === currency)
      priceSeries.addPrices(asset, Object.entries(parsed.prices).map(([time, price]) => ({ price, time: Number(time) })));
  };

  const fetchHistoricalAssetPrice = async (payload: HistoricalAssetPricePayload): Promise<HistoricalAssetPriceResponse> => {
    const asset = payload.asset;
    const currency = get(currencySymbol);
    const failedState = { ...get(failedDailyPrices) };
    const resolvedState = { ...get(resolvedFailedDailyPrices) };
    const failedTimestamps = failedState[asset]?.noPricesTimestamps || [];
    const resolvedTimestamps = resolvedState[asset] || [];

    const excludeTimestamps
      = failedTimestamps.filter(timestamp => !resolvedTimestamps.includes(timestamp));

    const empty: HistoricalAssetPriceResponse = {
      failedPricesTimestamps: [],
      noPricesTimestamps: [],
      prices: {},
      rateLimitedPricesTimestamps: [],
    };
    const outcome = await submitTask<HistoricalAssetPriceResponse>({
      id: dailyPricesActivity.id(payload),
      kind: dailyPricesActivity.kind,
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
          resetFailedStates(payload, parsed);
          publishPrices(asset, parsed, currency);
          return parsed;
        },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.daily'), { asset: getAssetField(payload.asset, 'name') }),
      title: t('task_center.group.prices'),
    });

    onActionableError(outcome, error => logger.error(error.message));

    return getOr(outcome, empty);
  };

  return {
    fetchHistoricalAssetPrice,
  };
}

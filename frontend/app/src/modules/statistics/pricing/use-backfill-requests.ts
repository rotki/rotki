import type { BackfillRequest } from '@/modules/statistics/pricing/backfill-plan';
import { HistoricalAssetPriceResponse } from '@rotki/common';
import { map as mapResult } from 'plainfp/result';
import { msg } from '@/message-key';
import { priceBackfillActivity } from '@/modules/assets/prices/prices.activity';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { logger } from '@/modules/core/common/logging/logging';
import { isCancellation } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * How a request ended: priced (ok), throttled by an oracle (retried after a backoff), failed
 * outright (its days are recorded as having no price), cancelled, or overtaken by a currency switch.
 */
type RequestResult = 'ok' | 'rate-limited' | 'failed' | 'cancelled' | 'stale';

interface UseBackfillRequestsReturn {
  /** Runs one request and files its prices and its days without one. */
  readonly runRequest: (request: BackfillRequest) => Promise<RequestResult>;
  /** Cancels every backfill request in flight. */
  readonly cancelAll: () => void;
}

/** The days a request asks for. */
function requestedDays(request: BackfillRequest): number[] {
  const excluded = new Set(request.excludeTimestamps);
  const days: number[] = [];
  for (let day = request.fromTimestamp; day <= request.toTimestamp; day += SECONDS_PER_DAY) {
    if (!excluded.has(day))
      days.push(day);
  }
  return days;
}

/**
 * Runs backfill requests against `/balances/historical/asset/prices` as task center activities.
 *
 * @remarks
 * The backend prices in whatever main currency is set when it answers, so a response that arrives
 * after a currency switch is dropped rather than filed under the new currency. A request that fails
 * outright records its days as having no price: the backfill does not retry them this session, and
 * the user can add them by hand.
 */
export function useBackfillRequests(): UseBackfillRequestsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const currencySymbol = useSetting('currencySymbol');
  const store = usePriceSeriesStore();
  const { failedDailyPrices } = useHistoricPriceCache();
  const { queryHistoricalAssetPrices } = useStatisticsApi();
  const { cancelByPrefix, submitTask } = useNativeTask();
  const { getAssetField } = useAssetInfoRetrieval();

  function recordFailures(asset: string, noPricesTimestamps: readonly number[], rateLimitedPricesTimestamps: readonly number[]): void {
    if (noPricesTimestamps.length === 0)
      return;
    const current = get(failedDailyPrices);
    const previous = current[asset];
    set(failedDailyPrices, {
      ...current,
      [asset]: {
        noPricesTimestamps: [...new Set([...(previous?.noPricesTimestamps ?? []), ...noPricesTimestamps])],
        rateLimitedPricesTimestamps: [...rateLimitedPricesTimestamps],
      },
    });
  }

  async function runRequest(request: BackfillRequest): Promise<RequestResult> {
    const currency = get(currencySymbol);
    const subject = {
      asset: request.asset,
      fromTimestamp: request.fromTimestamp,
      interval: SECONDS_PER_DAY,
      toTimestamp: request.toTimestamp,
    };
    const outcome = await submitTask<HistoricalAssetPriceResponse>({
      id: priceBackfillActivity.id(subject),
      kind: priceBackfillActivity.kind,
      run: async ({ runTask }) => mapResult(
        await runTask<HistoricalAssetPriceResponse>(async () => queryHistoricalAssetPrices({
          ...subject,
          excludeTimestamps: request.excludeTimestamps,
        })),
        result => HistoricalAssetPriceResponse.parse(result),
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.backfill'), { asset: getAssetField(request.asset, 'name') }),
      title: t('task_center.group.prices'),
    });

    if (get(currencySymbol) !== currency)
      return 'stale';
    if (!outcome.ok) {
      if (isCancellation(outcome.error))
        return 'cancelled';
      logger.error(outcome.error.message);
      recordFailures(request.asset, requestedDays(request), []);
      return 'failed';
    }
    const response = outcome.value;
    store.addPrices(request.asset, Object.entries(response.prices).map(([time, price]) => ({ price, time: Number(time) })));
    recordFailures(request.asset, response.noPricesTimestamps, response.rateLimitedPricesTimestamps);
    return response.rateLimitedPricesTimestamps.length > 0 ? 'rate-limited' : 'ok';
  }

  function cancelAll(): void {
    cancelByPrefix(priceBackfillActivity.kind, ...priceBackfillActivity.partsWithin([]));
  }

  return { cancelAll, runRequest };
}

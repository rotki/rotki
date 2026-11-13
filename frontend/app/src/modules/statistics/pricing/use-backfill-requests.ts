import type { BackfillRequest } from '@/modules/statistics/pricing/backfill-plan';
import { HistoricalAssetPriceResponse } from '@rotki/common';
import { pipe } from 'plainfp';
import { fromZod } from 'plainfp/interop/zod';
import { flatMap, mapError, match, type Result, tap, tapError } from 'plainfp/result';
import { ZodError } from 'zod';
import { msg } from '@/message-key';
import { priceBackfillActivity } from '@/modules/assets/prices/prices.activity';
import { useHistoricPriceCache } from '@/modules/assets/prices/use-historic-price-cache';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { isActionable, isCancellation, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { usePriceSeriesStore } from '@/modules/statistics/pricing/use-price-series-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * How a request ended: priced (ok), throttled by an oracle (retried after a backoff), failed
 * outright (the backend or the network, so its days are skipped this session after a backoff),
 * answered with a response that does not match the schema (a bug on our side), cancelled, or
 * overtaken by a currency switch. Only days the backend reports as having no price are recorded
 * as such; a failure says nothing about the oracles.
 */
export type RequestResult = 'ok' | 'rate-limited' | 'failed' | 'invalid' | 'cancelled' | 'stale';

const parseResponse = fromZod(HistoricalAssetPriceResponse);

interface UseBackfillRequestsReturn {
  /** Runs one request and files its prices and its days without one. */
  readonly runRequest: (request: BackfillRequest) => Promise<RequestResult>;
  /** Cancels every backfill request in flight. */
  readonly cancelAll: () => void;
}

/** Whether a task failed because the backend's answer did not match the response schema. */
function isInvalidResponse(error: TaskError): boolean {
  return isActionable(error) && error.cause instanceof ZodError;
}

/** How a request that was not overtaken by a currency switch ended. */
export function classifyOutcome(outcome: Result<HistoricalAssetPriceResponse, TaskError>): Exclude<RequestResult, 'stale'> {
  return match(outcome, {
    err: (error) => {
      if (isCancellation(error))
        return 'cancelled';
      return isInvalidResponse(error) ? 'invalid' : 'failed';
    },
    ok: response => (response.rateLimitedPricesTimestamps.length > 0 ? 'rate-limited' : 'ok'),
  });
}

/**
 * Runs backfill requests against `/balances/historical/asset/prices` as task center activities.
 *
 * @remarks
 * The backend prices in whatever main currency is set when it answers, so a response that arrives
 * after a currency switch is dropped rather than filed under the new currency. Days the backend
 * reports as having no price are recorded, so the user can add them by hand. The response is parsed
 * inside the task, so a malformed one shows as a failed activity.
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
      run: async ({ runTask }) => flatMap(
        await runTask<unknown>(async () => queryHistoricalAssetPrices({
          ...subject,
          excludeTimestamps: request.excludeTimestamps,
        })),
        response => mapError(parseResponse(response), (error): TaskError => TaskFailed({ cause: error, message: getErrorMessage(error) })),
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.prices.backfill'), { asset: getAssetField(request.asset, 'name') }),
      title: t('task_center.group.prices'),
    });

    if (get(currencySymbol) !== currency)
      return 'stale';
    const result = classifyOutcome(outcome);
    pipe(
      outcome,
      tap((response) => {
        store.addPrices(request.asset, Object.entries(response.prices).map(([time, price]) => ({ price, time: Number(time) })));
        recordFailures(request.asset, response.noPricesTimestamps, response.rateLimitedPricesTimestamps);
      }),
      tapError((error) => {
        if (result !== 'cancelled')
          logger.error(error.message);
      }),
    );
    return result;
  }

  function cancelAll(): void {
    cancelByPrefix(priceBackfillActivity.kind, ...priceBackfillActivity.partsWithin([]));
  }

  return { cancelAll, runRequest };
}

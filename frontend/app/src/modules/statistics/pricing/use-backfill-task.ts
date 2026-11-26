import type { BackfillRequest } from '@/modules/statistics/pricing/backfill-plan';
import { HistoricalAssetPriceResponse } from '@rotki/common';
import { fromZod } from 'plainfp/interop/zod';
import { flatMap, mapError, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { priceBackfillActivity } from '@/modules/assets/prices/prices.activity';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { SECONDS_PER_DAY } from '@/modules/core/common/constraints';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useStatisticsApi } from '@/modules/statistics/api/use-statistics-api';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

const parseResponse = fromZod(HistoricalAssetPriceResponse);

interface UseBackfillTaskReturn {
  /** Asks the backend for the daily prices of one request, as a task center activity. */
  readonly submitBackfill: (request: BackfillRequest) => Promise<Result<HistoricalAssetPriceResponse, TaskError>>;
  /** Cancels every backfill request in flight. */
  readonly cancelAll: () => void;
}

/**
 * Submits backfill requests against `/balances/historical/asset/prices` as task center activities.
 *
 * @remarks
 * The response is parsed inside the task, so a malformed one shows as a failed activity.
 */
export function useBackfillTask(): UseBackfillTaskReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { queryHistoricalAssetPrices } = useStatisticsApi();
  const { cancelByPrefix, submitTask } = useNativeTask();
  const { getAssetField } = useAssetInfoRetrieval();

  async function submitBackfill(request: BackfillRequest): Promise<Result<HistoricalAssetPriceResponse, TaskError>> {
    const subject = {
      asset: request.asset,
      fromTimestamp: request.fromTimestamp,
      interval: SECONDS_PER_DAY,
      toTimestamp: request.toTimestamp,
    };
    return submitTask<HistoricalAssetPriceResponse>({
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
  }

  function cancelAll(): void {
    cancelByPrefix(priceBackfillActivity.kind, ...priceBackfillActivity.partsWithin([]));
  }

  return { cancelAll, submitBackfill };
}

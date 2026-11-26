import type { ExchangeSavingsCollectionResponse, ExchangeSavingsRequestPayload } from '@/modules/balances/types/exchanges';
import type { TaskError } from '@/modules/core/tasks/task-result';
import { toSentenceCase } from '@rotki/common';
import { map as mapResult, type Result } from 'plainfp/result';
import { useI18n } from 'vue-i18n';
import { msg } from '@/message-key';
import { useExchangeApi } from '@/modules/balances/api/use-exchange-api';
import { exchangeSavingsActivity } from '@/modules/balances/balances.activity';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseExchangeSavingsSyncReturn {
  syncExchangeSavings: (location: string) => Promise<void>;
}

/**
 * Submits the backend refresh of an exchange's savings interest to the task center.
 */
export function useExchangeSavingsSync(): UseExchangeSavingsSyncReturn {
  const { submitTask } = useNativeTask();
  const { getExchangeSavingsTask } = useExchangeApi();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * Asks the backend to refresh one location's savings interest, as a task center activity.
   *
   * @remarks
   * Nothing is returned to the caller: the task only refills the backend cache, which the detail
   * view re-reads through `fetchExchangeSavings` once the activity settles. The activity id is
   * keyed by location, so each connected exchange gets its own row and its own rerun.
   * @param location - a connected exchange location that has a savings history
   */
  const syncExchangeSavings = async (location: string): Promise<void> => {
    const defaults: ExchangeSavingsRequestPayload = {
      ascending: [false],
      limit: 0,
      location,
      offset: 0,
      orderByAttributes: ['timestamp'],
    };

    await submitTask({
      id: exchangeSavingsActivity.id({ location }),
      kind: exchangeSavingsActivity.kind,
      lane: exchangeSavingsActivity.laneOf?.({ location }),
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<ExchangeSavingsCollectionResponse>(
          async () => getExchangeSavingsTask(defaults),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.exchange_savings.interest'), { location: toSentenceCase(location) }),
      title: t('task_center.group.exchange_savings'),
    });
  };

  return { syncExchangeSavings };
}

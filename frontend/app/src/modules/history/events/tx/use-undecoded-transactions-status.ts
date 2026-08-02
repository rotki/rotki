import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { snakeCaseTransformer } from '@/modules/core/api/transformers';
import { logger } from '@/modules/core/common/logging/logging';
import { EvmUndecodedTransactionResponse } from '@/modules/core/messaging/types';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseUndecodedTransactionsStatusReturn {
  fetchUndecodedTransactionsBreakdown: () => Promise<void>;
}

/**
 * How many transactions are still undecoded, per chain.
 *
 * Read-only against the backend and separate from the decoding it informs: the count is what a
 * refresh consults to decide whether a decode has anything to do, what the decoding-status UI
 * renders, and what a redecode reads before it starts — none of which is decoding.
 */
export function useUndecodedTransactionsStatus(): UseUndecodedTransactionsStatusReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { getUndecodedTransactionsBreakdown } = useHistoryEventsApi();
  const { statusOf, submitTask } = useNativeTask();
  const { resetUndecodedTransactionsStatus, updateUndecodedTransactionsStatus } = useDecodingStatusStore();

  const fetchUndecodedTransactionsBreakdown = async (): Promise<void> => {
    if (statusOf(ActivityKind.HISTORY_EVENTS, ActivityPart.UNDECODED).active) {
      logger.debug(`was already fetching undecoded transactions`);
      return;
    }

    const title = t('actions.history.fetch_undecoded_transactions.task.title');

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.UNDECODED),
      kind: ActivityKind.HISTORY_EVENTS,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<EvmUndecodedTransactionResponse>(
          async () => getUndecodedTransactionsBreakdown(),
        ),
        (result) => {
          const breakdown = EvmUndecodedTransactionResponse.parse(snakeCaseTransformer(result));

          if (Object.keys(breakdown).length > 0) {
            updateUndecodedTransactionsStatus(
              Object.fromEntries(
                Object.entries(breakdown).map(([chain, entry]) => [
                  chain,
                  {
                    chain,
                    processed: 0,
                    total: entry.undecoded,
                  },
                ]),
              ),
            );
          }
          else {
            resetUndecodedTransactionsStatus();
          }
        },
      ),
      subtitle: activityLabel(ActivityKind.HISTORY_EVENTS, ActivityPart.UNDECODED),
      title: t('task_center.group.history_events'),
    });

    if (isErr(outcome) && isActionable(outcome.error)) {
      const description = t('actions.history.fetch_undecoded_transactions.error.message', {
        message: outcome.error.message,
      });
      notifyError(title, description);
    }
  };

  return {
    fetchUndecodedTransactionsBreakdown,
  };
}

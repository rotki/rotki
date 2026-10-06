import type { TaskError } from '@/modules/core/tasks/task-result';
import { map as mapResult, type Result } from 'plainfp/result';
import { snakeCaseTransformer } from '@/modules/core/api/transformers';
import { logger } from '@/modules/core/common/logging/logging';
import { EvmUndecodedTransactionResponse } from '@/modules/core/messaging/types';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { type ActivityId, ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/** The undecoded-count fetch's activity, which a decode can wait for so its progress starts from it. */
export const UNDECODED_BREAKDOWN_ID = makeActivityId(ActivityKind.HISTORY_EVENTS, ActivityPart.UNDECODED);

interface UseUndecodedTransactionsStatusReturn {
  fetchUndecodedTransactionsBreakdown: (parent?: ActivityId) => Promise<void>;
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
  const { getUndecodedTransactionsBreakdown } = useHistoryEventsApi();
  const { statusOf, submitTask } = useNativeTask();
  const { resetUndecodedTransactionsStatus, updateUndecodedTransactionsStatus } = useDecodingStatusStore();

  const fetchUndecodedTransactionsBreakdown = async (parent?: ActivityId): Promise<void> => {
    if (statusOf(ActivityKind.HISTORY_EVENTS, ActivityPart.UNDECODED).active) {
      logger.debug(`was already fetching undecoded transactions`);
      return;
    }

    await submitTask({
      id: UNDECODED_BREAKDOWN_ID,
      kind: ActivityKind.HISTORY_EVENTS,
      parent,
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
  };

  return {
    fetchUndecodedTransactionsBreakdown,
  };
}

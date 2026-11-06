import type { Ref } from 'vue';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { currentBalanceDetectionActivity } from '@/modules/history/balances/historical-balances.activity';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseDataIssuesDetectionReturn {
  detecting: Readonly<Ref<boolean>>;
  /** Why the last comparison failed, for the page to name with a retry; cleared when the next one starts. */
  detectFailure: Readonly<Ref<NamedFailure | undefined>>;
  /**
   * Compares the balances rotki derived from events with the live chain balances, writing a data
   * issue for each difference, then calls `reload`. A failure to start, for example while the
   * historical balances are still being processed, is kept in `detectFailure`.
   */
  detect: () => Promise<void>;
}

/**
 * @param reload - reloads the issues list once the comparison has finished
 */
export function useDataIssuesDetection(reload: () => Promise<void>): UseDataIssuesDetectionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const detecting = shallowRef<boolean>(false);
  const { failure: detectFailure, run } = useFailureSlot();
  const { triggerTask } = useTaskApi();
  const { submitTask } = useNativeTask();

  async function runDetection(): Promise<Result<boolean, TaskError>> {
    return submitTask<boolean>({
      id: currentBalanceDetectionActivity.id(),
      kind: currentBalanceDetectionActivity.kind,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => runTask<boolean>(
        async () => triggerTask('current_balance_detection'),
        { conflictFails: true },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.historical_balances.detection')),
      title: t('task_center.group.historical_balances'),
    });
  }

  /**
   * Runs the comparison and reloads the list unless it failed.
   *
   * @remarks
   * A cancelled or skipped comparison still reloads and names nothing; only an actionable failure
   * is reported, worded as the task worded it.
   */
  async function detect(): Promise<void> {
    set(detecting, true);
    await run(t('data_issues.detect.error'), async () => {
      const outcome = await runDetection();
      if (isErr(outcome) && isActionable(outcome.error))
        return err(outcome.error.message);
      await reload();
      return ok(undefined);
    });
    set(detecting, false);
  }

  return {
    detect,
    detectFailure,
    detecting: readonly(detecting),
  };
}

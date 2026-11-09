import type { Ref } from 'vue';
import { FetchError } from 'ofetch';
import { err, isErr, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { errorOf, isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { currentBalanceDetectionActivity } from '@/modules/history/balances/historical-balances.activity';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/** How a check attempt ended, for a caller that shows the refusal inline. */
export interface DetectionResult {
  success: boolean;
  /** The backend refused because history work is running (HTTP 409). */
  conflict: boolean;
  message?: string;
}

export interface UseDataIssuesDetectionReturn {
  detecting: Readonly<Ref<boolean>>;
  /** Why the last comparison failed, for the page to name with a retry; cleared when the next one starts. */
  detectFailure: Readonly<Ref<NamedFailure | undefined>>;
  /**
   * Compares the balances rotki derived from events with the live chain balances, writing a data
   * issue for each difference, then calls `reload`. A failure to start, for example while the
   * historical balances are still being processed, is kept in `detectFailure` for the page, and a
   * 409 is also returned to the caller as a conflict to show inline.
   */
  detect: () => Promise<DetectionResult>;
}

function isStartConflict(error: unknown): boolean {
  return error instanceof FetchError && (error.status === 409 || error.statusCode === 409);
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
   * is reported, worded as the task worded it. The failure is also returned so a caller such as
   * reconciliation can tell a 409 refusal from any other failure.
   */
  async function detect(): Promise<DetectionResult> {
    set(detecting, true);
    let result: DetectionResult = { conflict: false, success: true };
    await run(t('data_issues.detect.error'), async () => {
      const outcome = await runDetection();
      if (isErr(outcome) && isActionable(outcome.error)) {
        const { message } = outcome.error;
        result = { conflict: isStartConflict(errorOf(outcome.error)), message, success: false };
        return err(message);
      }

      try {
        await reload();
      }
      catch (error: unknown) {
        result = { conflict: false, message: getErrorMessage(error), success: false };
        throw error;
      }

      return ok(undefined);
    });
    set(detecting, false);
    return result;
  }

  return {
    detect,
    detectFailure,
    detecting: readonly(detecting),
  };
}

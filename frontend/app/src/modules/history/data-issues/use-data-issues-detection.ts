import type { Result } from 'plainfp/result';
import type { Ref } from 'vue';
import { msg } from '@/message-key';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { useTaskApi } from '@/modules/core/tasks/use-task-api';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseDataIssuesDetectionReturn {
  detecting: Readonly<Ref<boolean>>;
  /**
   * Compares the balances rotki derived from events with the live chain balances, writing a data
   * issue for each difference, then calls `reload`. A failure to start, for example while the
   * historical balances are still being processed, is shown as an error notification.
   */
  detect: () => Promise<void>;
}

/**
 * @param reload - reloads the issues list once the comparison has finished
 */
export function useDataIssuesDetection(reload: () => Promise<void>): UseDataIssuesDetectionReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const detecting = shallowRef<boolean>(false);
  const { triggerTask } = useTaskApi();
  const { submitTask } = useNativeTask();

  async function runDetection(): Promise<void> {
    const outcome = await submitTask<boolean>({
      id: makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.DETECT),
      kind: ActivityKind.HISTORICAL_BALANCES,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<boolean, TaskError>> => runTask<boolean>(
        async () => triggerTask('current_balance_detection'),
        { conflictFails: true },
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.historical_balances.detection')),
      title: t('task_center.group.historical_balances'),
    });

    onActionableError(outcome, (error) => {
      throw new Error(error.message);
    });
  }

  async function detect(): Promise<void> {
    set(detecting, true);
    try {
      await runDetection();
      await reload();
    }
    catch (error: unknown) {
      showErrorMessage(t('data_issues.detect.action'), t('data_issues.detect.error', { error: getErrorMessage(error) }));
    }
    finally {
      set(detecting, false);
    }
  }

  return {
    detect,
    detecting: readonly(detecting),
  };
}

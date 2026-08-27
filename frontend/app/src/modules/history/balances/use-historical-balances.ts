import { map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { onActionableError, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseHistoricalBalancesReturn {
  triggerHistoricalBalancesProcessing: () => Promise<void>;
}

/**
 * Triggers backend historical-balance processing as one HISTORICAL_BALANCES activity.
 *
 * @remarks
 * The orchestrator owns its liveness, progress, cancellation and re-run, which is what lets the
 * smart re-run policy fire when an event edit invalidates historical balances. This fires the
 * single backend task and awaits it; the backend streams fine-grained progress over the websocket,
 * which the progress handler pushes onto the activity through `orchestrator.reportProgress` rather
 * than into a parallel status store.
 */
export function useHistoricalBalances(): UseHistoricalBalancesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { processHistoricalBalances } = useHistoricalBalancesApi();
  const { submitTask } = useNativeTask();

  async function triggerHistoricalBalancesProcessing(): Promise<void> {
    if (!import.meta.env.VITE_ACCOUNTING_UPDATE) {
      return;
    }

    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.HISTORICAL_BALANCES),
      kind: ActivityKind.HISTORICAL_BALANCES,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => processHistoricalBalances(),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.historical_balances.processing')),
      title: t('task_center.group.historical_balances'),
    });

    onActionableError(outcome, (error) => {
      throw new Error(error.message);
    });
  }

  return {
    triggerHistoricalBalancesProcessing,
  };
}

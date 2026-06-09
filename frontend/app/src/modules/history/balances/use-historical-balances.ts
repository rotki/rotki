import type { TaskMeta } from '@/modules/core/tasks/types';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';

interface UseHistoricalBalancesReturn {
  triggerHistoricalBalancesProcessing: () => Promise<void>;
}

export function useHistoricalBalances(): UseHistoricalBalancesReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { processHistoricalBalances } = useHistoricalBalancesApi();
  const { runTask } = useTaskHandler();

  async function triggerHistoricalBalancesProcessing(): Promise<void> {
    if (!import.meta.env.VITE_ACCOUNTING_UPDATE) {
      return;
    }

    const outcome = await runTask<boolean, TaskMeta>(
      async () => processHistoricalBalances(),
      {
        type: TaskType.PROCESS_HISTORICAL_BALANCES,
        meta: {
          title: t('historical_balances.title'),
          description: t('historical_balances.processing_description'),
        },
      },
    );

    if (isActionableFailure(outcome))
      throw outcome.error instanceof Error ? outcome.error : new Error(outcome.message);
  }

  return {
    triggerHistoricalBalancesProcessing,
  };
}

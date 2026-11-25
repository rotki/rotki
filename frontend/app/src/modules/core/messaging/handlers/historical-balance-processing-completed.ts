import type { StateHandler } from '../interfaces';
import { z } from 'zod';
import { createStateHandler } from '@/modules/core/messaging/utils';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { CostBasisStalled } from '@/modules/task-center/background/background-task-types';
import { useBackgroundTasks } from '@/modules/task-center/background/use-background-tasks';

const HistoricalBalanceProcessingCompletedData = z.object({
  costBasisStalled: CostBasisStalled.optional(),
});

export function createHistoricalBalanceProcessingCompletedHandler(): StateHandler {
  const { notifyHistoricalBalanceProcessingCompleted } = useHistoricalBalanceProcessingStore();
  const { syncCostBasisStalled } = useBackgroundTasks();
  return createStateHandler((data) => {
    notifyHistoricalBalanceProcessingCompleted();
    const parsed = HistoricalBalanceProcessingCompletedData.safeParse(data);
    syncCostBasisStalled(parsed.success ? parsed.data.costBasisStalled : undefined);
  });
}

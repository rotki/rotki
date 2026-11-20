import type { HistoricalBalanceProcessingData } from '@/modules/core/messaging/types/status-types';
import { historicalBalancesActivity } from '@/modules/history/balances/historical-balances.activity';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { BackgroundTaskKind } from '@/modules/task-center/background/background-task-types';
import { backgroundTaskActivity } from '@/modules/task-center/background/background-task.activity';
import { type ActivityId, activityIdHasPrefix } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

interface UseHistoricalBalancesProgressReturn {
  reportHistoricalBalancesProgress: (data: HistoricalBalanceProcessingData) => void;
}

/**
 * Whether the activity is a row that shows a historical balance processing run.
 *
 * @remarks
 * A run shows as the background task row mirroring it, whoever started it, and while a user's
 * trigger is awaited also as the `historical-balances` activity. The rest of the kind's activities
 * (series, divergence, detection) are other work.
 */
export function showsHistoricalBalancesProcessing(id: ActivityId): boolean {
  return id === historicalBalancesActivity.id()
    || activityIdHasPrefix(id, backgroundTaskActivity.kind, BackgroundTaskKind.HISTORICAL_BALANCES);
}

/**
 * Reports the backend's historical balance processing frames onto the rows that show the run.
 *
 * @remarks
 * The trigger a user starts settles as soon as the backend has scheduled the run, and a run the
 * task manager starts on its own has no trigger at all, so the frames go to the background task row
 * as well. The orchestrator ignores whichever row is not running.
 */
export function useHistoricalBalancesProgress(): UseHistoricalBalancesProgressReturn {
  const { reportProgress, reportProgressByPrefix } = useTaskOrchestrator();
  const { notifyHistoricalBalanceProcessingProgressed } = useHistoricalBalanceProcessingStore();

  function reportHistoricalBalancesProgress({ phase, processed, total }: HistoricalBalanceProcessingData): void {
    const steps = { current: processed, total };
    reportProgress(historicalBalancesActivity.id(), steps);
    reportProgressByPrefix(steps, backgroundTaskActivity.kind, BackgroundTaskKind.HISTORICAL_BALANCES);
    notifyHistoricalBalanceProcessingProgressed(phase);
  }

  return { reportHistoricalBalancesProgress };
}

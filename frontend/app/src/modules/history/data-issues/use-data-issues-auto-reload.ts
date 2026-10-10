import { startPromise } from '@shared/utils';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

/**
 * Reloads the issues when something that detects them has finished.
 *
 * @remarks
 * A finished sync and a finished historical balance processing are what detect new issues, so the
 * list reloads on them rather than waiting for the poll.
 *
 * @param reload - reloads the list and its summary
 */
export function useDataIssuesAutoReload(reload: () => Promise<void>): void {
  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { syncCompleted } = useSyncCompleted();

  watch([syncCompleted, historicalBalanceProcessingCompleted], () => {
    startPromise(reload());
  });
}

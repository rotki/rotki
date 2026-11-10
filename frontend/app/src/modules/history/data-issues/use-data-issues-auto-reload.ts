import { startPromise } from '@shared/utils';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useDataIssueRemediationStore } from '@/modules/history/data-issues/use-data-issue-remediation-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

/**
 * Reloads the issues when something that changes them has finished.
 *
 * @remarks
 * A finished sync, a finished historical balance processing and a finished current balance
 * detection are what detect new issues, and a finished auto-remediation run is what resolves or
 * re-states them, so the list reloads on them rather than waiting for the poll. The detection runs
 * after the processing it follows has already reported completion.
 *
 * @param reload - reloads the list and its summary
 */
export function useDataIssuesAutoReload(reload: () => Promise<void>): void {
  const { currentBalanceDetectionCompleted, historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { remediationCompleted } = storeToRefs(useDataIssueRemediationStore());
  const { syncCompleted } = useSyncCompleted();

  watch([syncCompleted, historicalBalanceProcessingCompleted, currentBalanceDetectionCompleted, remediationCompleted], () => {
    startPromise(reload());
  });
}

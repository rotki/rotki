import { startPromise } from '@shared/utils';
import { storeToRefs } from 'pinia';
import { onScopeDispose, watch } from 'vue';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useDataIssueRemediationStore } from '@/modules/history/data-issues/use-data-issue-remediation-store';
import { useDataIssuesInboxStore } from '@/modules/history/data-issues/use-data-issues-inbox-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

/**
 * Reloads the issues when something that changes them has finished.
 *
 * @remarks
 * A finished sync, a finished historical balance processing and a finished current balance
 * detection are what detect new issues; a finished auto-remediation run resolves or re-states
 * them; and external mutations such as marking tokens as spam remove their persisted issues.
 *
 * @param reload - reloads the list and its summary
 */
export function useDataIssuesAutoReload(reload: () => Promise<void>): void {
  const { currentBalanceDetectionCompleted, historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { remediationCompleted } = storeToRefs(useDataIssueRemediationStore());
  const inboxStore = useDataIssuesInboxStore();
  const { issuesInvalidated } = storeToRefs(inboxStore);
  const { syncCompleted } = useSyncCompleted();

  inboxStore.incrementReloadListeners();
  onScopeDispose(() => inboxStore.decrementReloadListeners());

  watch([syncCompleted, historicalBalanceProcessingCompleted, currentBalanceDetectionCompleted, remediationCompleted, issuesInvalidated], () => {
    startPromise(reload());
  });
}

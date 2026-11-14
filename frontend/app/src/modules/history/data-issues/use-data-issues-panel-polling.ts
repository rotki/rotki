import type { MaybeRefOrGetter } from 'vue';
import { startPromise } from '@shared/utils';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useDataIssueRemediationStore } from '@/modules/history/data-issues/use-data-issue-remediation-store';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

/** How often the panel re-reads the list while auto-remediation is running. */
const POLL_INTERVAL = 10_000;

/**
 * Keeps the panel's list fresh without letting a backgrounded panel hit the network.
 *
 * Three triggers reload it: a slow poll while any row is auto-remediating, the completion of a
 * history sync, a historical balance processing or a current balance detection (so the inbox
 * reflects freshly detected issues, or the all-clear shield, without waiting for the poll or a
 * manual refresh), and the end of an auto-remediation run, which is what resolves or re-states
 * the rows.
 *
 * All are gated on activation, because under `<KeepAlive>` a hidden panel keeps its reactivity
 * live. A completion that arrives while hidden is not dropped: it is recorded and caught up the
 * next time the panel is shown.
 */
export function useDataIssuesPanelPolling(
  hasRemediatingRows: MaybeRefOrGetter<boolean>,
  reload: () => Promise<void>,
): void {
  const { syncCompleted } = useSyncCompleted();
  const { currentBalanceDetectionCompleted, historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { remediationCompleted } = storeToRefs(useDataIssueRemediationStore());
  const { pause, resume } = useIntervalFn(() => {
    startPromise(reload());
  }, POLL_INTERVAL, { immediate: false });

  const active = shallowRef<boolean>(true);
  const pendingRefresh = shallowRef<boolean>(false);

  function syncPolling(): void {
    if (get(active) && toValue(hasRemediatingRows))
      resume();
    else
      pause();
  }

  watch(() => toValue(hasRemediatingRows), syncPolling);

  watch(syncCompleted, () => {
    if (get(active))
      startPromise(reload());
    else
      set(pendingRefresh, true);
  });

  watch([historicalBalanceProcessingCompleted, currentBalanceDetectionCompleted, remediationCompleted], () => {
    if (get(active))
      startPromise(reload());
    else
      set(pendingRefresh, true);
  });

  onActivated(() => {
    set(active, true);
    syncPolling();
    if (get(pendingRefresh)) {
      set(pendingRefresh, false);
      startPromise(reload());
    }
  });

  onDeactivated(() => {
    set(active, false);
    pause();
  });
}

import type { MaybeRefOrGetter } from 'vue';
import { startPromise } from '@shared/utils';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

/** How often the panel re-reads the list while auto-remediation is running. */
const POLL_INTERVAL = 10_000;

/**
 * Keeps the panel's list fresh without letting a backgrounded panel hit the network.
 *
 * Two triggers reload it: a slow poll while any row is auto-remediating, and the
 * completion of a history sync (so the inbox reflects freshly detected issues, or
 * the all-clear shield, without waiting for the poll or a manual refresh).
 *
 * Both are gated on activation, because under `<KeepAlive>` a hidden panel keeps its
 * reactivity live. A sync that completes while hidden is not dropped: it is recorded
 * and caught up the next time the panel is shown.
 */
export function useDataIssuesPanelPolling(
  hasRemediatingRows: MaybeRefOrGetter<boolean>,
  reload: () => Promise<void>,
): void {
  const { syncCompleted } = useSyncCompleted();
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

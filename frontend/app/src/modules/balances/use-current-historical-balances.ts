import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { useHistoricalSnapshotStore } from '@/modules/balances/use-historical-snapshot-store';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

export interface UseCurrentHistoricalBalancesReturn {
  /** Whether a load is in flight. */
  loading: Readonly<Ref<boolean>>;
  /** Load the current history-derived balances if they have not been requested yet. */
  ensureLoaded: () => Promise<void>;
  /** Re-fetch the current history-derived balances, dropping out-of-order responses. */
  refresh: () => Promise<void>;
  /** Trigger backend processing when the snapshot is behind recent event edits. */
  triggerProcessing: () => Promise<void>;
}

/**
 * Owns fetching the current history-derived balances into the snapshot store.
 *
 * @remarks
 * One shared instance serves every surface, so the dashboard and the asset page never send duplicate
 * requests. Nothing loads until a caller asks with `ensureLoaded`; after that, the snapshot reloads
 * when backend processing completes, when a history sync settles, and when the ignored assets
 * change. A monotonic request counter drops responses that arrive after a newer load started.
 *
 * The shared instance, its watchers with it, is disposed when the last page using it unmounts,
 * while the store keeps the snapshot. Changes made while no page was listening went unseen, so a
 * snapshot that is already loaded is refreshed each time a page sets this up again.
 */
export const useCurrentHistoricalBalances = createSharedComposable((): UseCurrentHistoricalBalancesReturn => {
  const store = useHistoricalSnapshotStore();
  const { loaded, loading } = storeToRefs(store);
  const { fetchCurrentHistoricalBalances } = useHistoricalBalancesApi();
  const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();
  const { historicalBalanceProcessingCompleted } = storeToRefs(useHistoricalBalanceProcessingStore());
  const { syncCompleted } = useSyncCompleted();
  const { ignoredAssets } = storeToRefs(useAssetsStore());

  let latestRequest = 0;

  async function load(): Promise<void> {
    if (!isAccountingUpdateEnabled())
      return;

    const request = ++latestRequest;
    store.setLoading(true);
    store.setError(undefined);
    try {
      const response = await fetchCurrentHistoricalBalances();
      if (request !== latestRequest)
        return;

      store.setSnapshot({
        entries: response.entries,
        processingRequired: response.processingRequired,
        stale: response.stale,
      });
    }
    catch (error: unknown) {
      if (request !== latestRequest)
        return;
      logger.error(error);
      store.setError(error instanceof Error ? error.message : String(error));
    }
    finally {
      if (request === latestRequest)
        store.setLoading(false);
    }
  }

  async function ensureLoaded(): Promise<void> {
    if (!get(loaded) && !get(loading))
      await load();
  }

  async function triggerProcessing(): Promise<void> {
    await triggerHistoricalBalancesProcessing();
  }

  /** Refresh an already-loaded snapshot after an event that can change derived balances. */
  function refreshIfLoaded(): void {
    if (get(loaded))
      startPromise(load());
  }

  watch(historicalBalanceProcessingCompleted, refreshIfLoaded);
  watch(syncCompleted, refreshIfLoaded);
  watch(ignoredAssets, refreshIfLoaded);

  refreshIfLoaded();

  return {
    ensureLoaded,
    loading: readonly(loading),
    refresh: load,
    triggerProcessing,
  };
});

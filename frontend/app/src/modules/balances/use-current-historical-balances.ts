import type { Ref } from 'vue';
import { startPromise } from '@shared/utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { useBalanceDisplayModeStore } from '@/modules/balances/use-balance-display-mode-store';
import { isAccountingUpdateEnabled } from '@/modules/core/common/feature-flags';
import { logger } from '@/modules/core/common/logging/logging';
import { useHistoricalBalanceProcessingStore } from '@/modules/history/balances/use-historical-balance-processing-store';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useSyncCompleted } from '@/modules/shell/sync-progress/use-sync-completed';

export interface UseCurrentHistoricalBalancesReturn {
  /** Whether a load is in flight. */
  loading: Ref<boolean>;
  /** Load the current history-derived balances if they have not been requested yet. */
  ensureLoaded: () => Promise<void>;
  /** Re-fetch the current history-derived balances, dropping out-of-order responses. */
  refresh: () => Promise<void>;
  /** Trigger backend processing when the snapshot is behind recent event edits. */
  triggerProcessing: () => Promise<void>;
}

/**
 * Owns fetching the current history-derived balances into the display-mode store.
 *
 * @remarks
 * A single shared instance serves every surface (dashboard, blockchain page, asset detail), so
 * switching to `history` mode and the asset comparison line never trigger duplicate requests.
 * Reloads when backend processing completes, when a history sync settles (new events can change
 * derived balances), and when the ignored-asset list changes, but only once a snapshot has been
 * requested, so merely opening the dashboard in `queried` mode does not hit the endpoint. A
 * monotonic request counter drops responses that arrive after a newer load started.
 */
export const useCurrentHistoricalBalances = createSharedComposable((): UseCurrentHistoricalBalancesReturn => {
  const store = useBalanceDisplayModeStore();
  const { mode, loaded, loading } = storeToRefs(store);
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

  /** Refresh an already-requested snapshot after an event that can change derived balances. */
  function refreshIfRequested(): void {
    if (get(loaded))
      startPromise(load());
  }

  watch(mode, (newMode) => {
    if (newMode === 'history')
      startPromise(ensureLoaded());
  });

  watch(historicalBalanceProcessingCompleted, refreshIfRequested);
  watch(syncCompleted, refreshIfRequested);
  watch(ignoredAssets, refreshIfRequested);

  return {
    ensureLoaded,
    loading: readonly(loading),
    refresh: load,
    triggerProcessing,
  };
});

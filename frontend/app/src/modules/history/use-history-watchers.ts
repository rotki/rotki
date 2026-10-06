import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { useConnectedExchangesStore } from '@/modules/balances/exchanges/use-connected-exchanges-store';
import { useRefWithDebounce } from '@/modules/core/common/use-ref-debounce';
import { hasLiveSession } from '@/modules/core/session/session-lifecycle';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useUnmatchedAssetMovements } from '@/modules/history/events/use-unmatched-asset-movements';
import { useUnmatchedBridgeTransactions } from '@/modules/history/events/use-unmatched-bridge-transactions';
import { useHistoryDataFetching } from '@/modules/history/use-history-data-fetching';
import { useHistoryStore } from '@/modules/history/use-history-store';

const HISTORY_EVENTS_MODIFIED_DEBOUNCE_MS = 15_000;

/**
 * Reacts to history processing finishing: refreshes the status summary and runs the
 * post-processing steps.
 *
 * @remarks
 * Every reaction runs only while a session is live. These watchers live as long as the app, and
 * the store reset at logout ends processing after the session ended: reacting would start
 * post-processing for a user who is gone, or leave `postProcessing` set in the state the next
 * session starts from.
 */
export function useHistoryWatchers(): void {
  const { processing } = useHistoryEventsStatus();
  const { fetchTransactionStatusSummary } = useHistoryDataFetching();
  const historyStore = useHistoryStore();
  const { hasUnprocessedModifications } = storeToRefs(historyStore);
  const { triggerAssetMovementAutoMatching } = useUnmatchedAssetMovements();
  const { triggerBridgeAutoMatching } = useUnmatchedBridgeTransactions();
  const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();
  const { connectedExchanges } = storeToRefs(useConnectedExchangesStore());

  const processingDebounced = useRefWithDebounce(processing, 500);

  // Debounced reprocessing after manual event modifications
  watchDebounced(
    () => historyStore.eventsVersion,
    () => {
      if (hasLiveSession() && get(hasUnprocessedModifications)) {
        historyStore.acknowledgeModifications();
        startPromise(triggerHistoricalBalancesProcessing());
      }
    },
    { debounce: HISTORY_EVENTS_MODIFIED_DEBOUNCE_MS },
  );

  watch(
    [processing, connectedExchanges],
    async (
      [currentProcessing, connectedExchanges],
      [previousProcessing, previousConnectedExchanges],
    ) => {
      if (!hasLiveSession())
        return;

      if (
        currentProcessing !== previousProcessing ||
        !isEqual(connectedExchanges, previousConnectedExchanges)
      ) {
        await fetchTransactionStatusSummary();
      }
    },
  );

  watch(processing, (isProcessing, wasProcessing) => {
    if (hasLiveSession() && !isProcessing && wasProcessing)
      historyStore.setPostProcessing(true);
  });

  watch(processingDebounced, async (processing, wasProcessing) => {
    if (hasLiveSession() && !processing && wasProcessing) {
      try {
        historyStore.acknowledgeModifications();
        await triggerHistoricalBalancesProcessing();
        await triggerAssetMovementAutoMatching();
        await triggerBridgeAutoMatching();
      }
      finally {
        historyStore.setPostProcessing(false);
      }
    }
  });
}

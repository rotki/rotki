import { NotificationGroup } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { useUnmatchedAssetMovements } from '@/composables/history/events/use-unmatched-asset-movements';
import { useRefWithDebounce } from '@/composables/ref';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { Routes } from '@/router/routes';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useHistoryStore } from '@/store/history';
import { useNotificationsStore } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useSessionSettingsStore } from '@/store/settings/session';
import { BalanceSource } from '@/types/settings/frontend-settings';

export function useMonitorWatchers(): void {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { removeIgnoredAssets } = useBalancesStore();
  const { processing } = useHistoryEventsStatus();
  const { fetchTransactionStatusSummary, resetEventsModifiedSignal } = useHistoryStore();
  const { triggerAssetMovementAutoMatching } = useUnmatchedAssetMovements();
  const { triggerHistoricalBalancesProcessing } = useHistoricalBalances();
  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { removeMatching } = useNotificationsStore();
  const router = useRouter();

  const frontendStore = useFrontendSettingsStore();
  const { balanceValueThreshold } = storeToRefs(frontendStore);

  const { ignoredAssets } = storeToRefs(useIgnoredAssetsStore());

  const processingDebounced = useRefWithDebounce(processing, 500);

  watch(balanceValueThreshold, (current, old) => {
    if (!isEqual(current[BalanceSource.MANUAL], old[BalanceSource.MANUAL])) {
      startPromise(fetchManualBalances(true));
    }

    if (!isEqual(current[BalanceSource.EXCHANGES], old[BalanceSource.EXCHANGES])) {
      startPromise(fetchConnectedExchangeBalances(false));
    }

    if (!isEqual(current[BalanceSource.BLOCKCHAIN], old[BalanceSource.BLOCKCHAIN])) {
      startPromise(fetchBlockchainBalances());
    }
  });

  watch(ignoredAssets, (curr, prev) => {
    const removedAssets = prev.filter(asset => !curr.includes(asset));
    if (removedAssets.length > 0) {
      startPromise(fetchBlockchainBalances());
    }

    const addedAssets = curr.filter(asset => !prev.includes(asset));
    if (addedAssets.length > 0) {
      removeIgnoredAssets(curr);
    }
  });

  watch([processing, connectedExchanges], async ([currentProcessing, connectedExchanges], [previousProcessing, previousConnectedExchanges]) => {
    if (currentProcessing !== previousProcessing || !isEqual(connectedExchanges, previousConnectedExchanges)) {
      await fetchTransactionStatusSummary();
    }
  });

  watch(processingDebounced, async (processing, wasProcessing) => {
    if (!processing && wasProcessing) {
      resetEventsModifiedSignal();
      await triggerHistoricalBalancesProcessing();
      await triggerAssetMovementAutoMatching();
    }
  });

  watchImmediate(router.currentRoute, (to) => {
    if (to.path === Routes.HISTORY_EVENTS.toString()) {
      removeMatching(notification => notification.group === NotificationGroup.UNMATCHED_ASSET_MOVEMENTS);
    }
  });
}

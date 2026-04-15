import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

export function useBalanceWatchers(): void {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { removeIgnoredAssets } = useBalancesStore();

  const { balanceValueThreshold } = storeToRefs(useFrontendSettingsStore());
  const { ignoredAssets } = storeToRefs(useAssetsStore());

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
}

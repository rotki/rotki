import { startPromise } from '@shared/utils';
import { isEqual } from 'es-toolkit';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useExchanges } from '@/modules/balances/exchanges/use-exchanges';
import { useManualBalances } from '@/modules/balances/manual/use-manual-balances';
import { useBalanceHydration } from '@/modules/balances/use-balance-hydration';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { BalanceSource } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';

export function useBalanceWatchers(): void {
  const { fetchManualBalances } = useManualBalances();
  const { fetchConnectedExchangeBalances } = useExchanges();
  const { hydrate } = useBalanceHydration();
  const { removeIgnoredAssets } = useBalancesStore();

  const balanceValueThreshold = useSetting('balanceValueThreshold');
  const { ignoredAssets } = storeToRefs(useAssetsStore());

  watch(balanceValueThreshold, (current, old) => {
    if (!isEqual(current[BalanceSource.MANUAL], old[BalanceSource.MANUAL])) {
      startPromise(fetchManualBalances(true));
    }

    if (!isEqual(current[BalanceSource.EXCHANGES], old[BalanceSource.EXCHANGES])) {
      startPromise(fetchConnectedExchangeBalances(false));
    }

    if (!isEqual(current[BalanceSource.BLOCKCHAIN], old[BalanceSource.BLOCKCHAIN])) {
      startPromise(hydrate());
    }
  });

  watch(ignoredAssets, (curr, prev) => {
    const removedAssets = prev.filter(asset => !curr.includes(asset));
    if (removedAssets.length > 0) {
      startPromise(hydrate());
    }

    const addedAssets = curr.filter(asset => !prev.includes(asset));
    if (addedAssets.length > 0) {
      removeIgnoredAssets(curr);
    }
  });
}

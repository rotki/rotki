import type { ManualBalanceWithValue } from '@/modules/balances/types/manual-balances';
import { set } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { BalanceType } from '@/modules/balances/types/balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';

interface UseManualBalancesUpdateReturn {
  /**
   * Replaces the stored manual balances with `balances`, split into assets and liabilities by
   * their balance type.
   */
  updateBalances: (balances: ManualBalanceWithValue[]) => void;
}

/**
 * Writes the manual balances the backend returned into the balances store.
 */
export function useManualBalancesUpdate(): UseManualBalancesUpdateReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());

  function updateBalances(balances: ManualBalanceWithValue[]): void {
    const assets: ManualBalanceWithValue[] = [];
    const liabilities: ManualBalanceWithValue[] = [];

    for (const balance of balances) {
      if (balance.balanceType === BalanceType.LIABILITY) {
        liabilities.push(balance);
      }
      else {
        assets.push(balance);
      }
    }

    set(manualBalances, assets);
    set(manualLiabilities, liabilities);
  }

  return { updateBalances };
}

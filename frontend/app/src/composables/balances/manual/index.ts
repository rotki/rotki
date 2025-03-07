import type { AssetBalances } from '@/types/balances';
import type { ManualBalanceWithValue } from '@/types/manual-balances';
import type { Balance } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { useManualBalancesStore } from '@/store/balances/manual';
import { balanceSum } from '@/utils/calculation';

function toAssetBalances(balances: ManualBalanceWithValue[]): AssetBalances {
  const ownedAssets: AssetBalances = {};

  for (const { amount, asset, usdValue } of balances) {
    const balance: Balance = {
      amount,
      usdValue,
    };
    if (!ownedAssets[asset])
      ownedAssets[asset] = balance;
    else ownedAssets[asset] = balanceSum(ownedAssets[asset], balance);
  }
  return ownedAssets;
}

interface UseManualAssetBalancesReturn {
  balances: ComputedRef<AssetBalances>;
  liabilities: ComputedRef<AssetBalances>;
}

export function useManualAssetBalances(): UseManualAssetBalancesReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useManualBalancesStore());

  const balances = computed<AssetBalances>(() => toAssetBalances(get(manualBalances)));

  const liabilities = computed<AssetBalances>(() => toAssetBalances(get(manualLiabilities)));

  return {
    balances,
    liabilities,
  };
}

import { Balance } from '@rotki/common';
import { ComputedRef } from 'vue';
import { useManualBalancesStore } from '@/store/balances/manual';
import { AssetBalances } from '@/types/balances';
import { ManualBalanceWithValue } from '@/types/manual-balances';
import { balanceSum } from '@/utils/calculation';

const toAssetBalances = (balances: ManualBalanceWithValue[]): AssetBalances => {
  const ownedAssets: AssetBalances = {};

  for (const { asset, usdValue, amount } of balances) {
    const balance: Balance = {
      amount,
      usdValue
    };
    if (!ownedAssets[asset]) {
      ownedAssets[asset] = balance;
    } else {
      ownedAssets[asset] = balanceSum(ownedAssets[asset], balance);
    }
  }
  return ownedAssets;
};

export const useManualAssetBalances = () => {
  const { manualBalances, manualLiabilities } = storeToRefs(
    useManualBalancesStore()
  );

  const balances: ComputedRef<AssetBalances> = computed(() => {
    return toAssetBalances(get(manualBalances));
  });

  const liabilities: ComputedRef<AssetBalances> = computed(() => {
    return toAssetBalances(get(manualLiabilities));
  });

  return {
    balances,
    liabilities
  };
};

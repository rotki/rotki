import { type Balance } from '@rotki/common';
import { type AssetBalances } from '@/types/balances';
import { type ManualBalanceWithValue } from '@/types/manual-balances';

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

  const balances: ComputedRef<AssetBalances> = computed(() =>
    toAssetBalances(get(manualBalances))
  );

  const liabilities: ComputedRef<AssetBalances> = computed(() =>
    toAssetBalances(get(manualLiabilities))
  );

  return {
    balances,
    liabilities
  };
};

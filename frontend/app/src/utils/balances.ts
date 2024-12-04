import { balanceSum, bigNumberSum } from '@/utils/calculation';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { getSortItems } from '@/utils/assets';
import type {
  AssetBalance,
  AssetBalanceWithPrice,
  BigNumber,
  HasBalance,
  Writeable,
} from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBalances } from '@/types/balances';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { ComputedRef } from 'vue';
import type { DataTableSortData } from '@rotki/ui-library';
import type { AssetInfoReturn } from '@/composables/assets/retrieval';

export function mergeAssociatedAssets(
  totals: MaybeRef<AssetBalances>,
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>,
): ComputedRef<AssetBalances> {
  return computed(() => {
    const ownedAssets: AssetBalances = {};

    for (const [asset, value] of Object.entries(get(totals))) {
      const identifier = getAssociatedAssetIdentifier(asset);
      const associatedAsset: string = get(identifier);
      const ownedAsset = ownedAssets[associatedAsset];
      if (!ownedAsset)
        ownedAssets[associatedAsset] = { ...value };
      else ownedAssets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
    }
    return ownedAssets;
  });
}

export function mergeAssetBalances(a: AssetBalances, b: AssetBalances): AssetBalances {
  const merged = { ...a };
  for (const [asset, value] of Object.entries(b)) {
    if (merged[asset])
      merged[asset] = { ...balanceSum(merged[asset], value) };
    else merged[asset] = value;
  }
  return merged;
}

export function groupAssetBreakdown(
  breakdowns: AssetBreakdown[],
  groupBy: (item: AssetBreakdown) => string = (item: AssetBreakdown) => item.location + item.address,
): AssetBreakdown[] {
  const initial: Record<string, Writeable<AssetBreakdown>> = {};
  const grouped = breakdowns.reduce((acc, breakdown) => {
    const key = groupBy(breakdown);
    if (!acc[key])
      acc[key] = { ...breakdown, ...zeroBalance() };

    const balance = balanceSum(acc[key], breakdown);
    acc[key].amount = balance.amount;
    acc[key].usdValue = balance.usdValue;
    return acc;
  }, initial);

  return Object.values(grouped).sort((a, b) => sortDesc(a.usdValue, b.usdValue));
}

export function appendAssetBalance(
  value: AssetBalance,
  assets: AssetBalances,
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>,
): void {
  const identifier = getAssociatedAssetIdentifier(value.asset);
  const associatedAsset: string = get(identifier);
  const ownedAsset = assets[associatedAsset];
  if (!ownedAsset)
    assets[associatedAsset] = { ...value };
  else assets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
}

export function sumAssetBalances(
  balances: AssetBalances[],
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>,
): AssetBalances {
  const summed: AssetBalances = {};
  for (const balance of balances) {
    for (const [asset, value] of Object.entries(balance)) {
      const identifier = getAssociatedAssetIdentifier(asset);
      const associatedAsset: string = get(identifier);

      if (summed[associatedAsset])
        summed[associatedAsset] = balanceSum(value, summed[associatedAsset]);
      else summed[associatedAsset] = { ...value };
    }
  }
  return summed;
}

export function sum(balances: { usdValue: BigNumber }[]): BigNumber {
  return bigNumberSum(balances.map(account => account.usdValue));
}

export function balanceUsdValueSum(balances: HasBalance[]): BigNumber {
  return balances.reduce((sum, balance) => sum.plus(balance.balance.usdValue), Zero);
}

export function sortAssetBalances<T extends AssetBalance = AssetBalanceWithPrice>(data: T[], sort: DataTableSortData<T>, assetInfo: AssetInfoReturn): T[] {
  const sortItems = getSortItems<T>(asset => get(assetInfo(asset)));

  const sortBy = get(sort);
  if (!Array.isArray(sortBy) && sortBy?.column)
    return sortItems(data, [sortBy.column as keyof AssetBalance], [sortBy.direction === 'desc']);

  return data;
}

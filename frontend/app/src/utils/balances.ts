import type {
  AssetBalance,
  AssetBalanceWithPrice,
  BigNumber,
  Writeable,
} from '@rotki/common';
import type { DataTableSortData } from '@rotki/ui-library';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef } from 'vue';
import type { AssetInfoReturn } from '@/composables/assets/retrieval';
import type { AssetBalances } from '@/types/balances';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import { getSortItems } from '@/utils/assets';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { balanceSum, bigNumberSum } from '@/utils/calculation';

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
    acc[key].value = balance.value;
    return acc;
  }, initial);

  return Object.values(grouped).sort((a, b) => sortDesc(a.value, b.value));
}

export function appendAssetBalance(
  value: AssetBalance,
  assets: AssetBalances,
  assetAssociationMap: Record<string, string>,
): void {
  const identifier = assetAssociationMap?.[value.asset] ?? value.asset;
  const ownedAsset = assets[identifier];
  if (!ownedAsset)
    assets[identifier] = { ...value };
  else
    assets[identifier] = { ...balanceSum(ownedAsset, value) };
}

export function sum(balances: { value?: BigNumber; usdValue: BigNumber }[]): BigNumber {
  return bigNumberSum(balances.map(account => account.value ?? account.usdValue));
}

export function sortAssetBalances<T extends AssetBalance = AssetBalanceWithPrice>(data: T[], sort: DataTableSortData<T>, assetInfo: AssetInfoReturn): T[] {
  const sortItems = getSortItems<T>(asset => get(assetInfo(asset)));

  const sortBy = get(sort);
  if (!Array.isArray(sortBy) && sortBy?.column)
    return sortItems(data, [sortBy.column as keyof AssetBalance], [sortBy.direction === 'desc']);

  return data;
}

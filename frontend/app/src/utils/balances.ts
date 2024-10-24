import type {
  BigNumber,
  HasBalance,
  Writeable,
} from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { AssetBalance, AssetBalances } from '@/types/balances';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import type { ComputedRef } from 'vue';

export function removeZeroAssets(entries: AssetBalances): AssetBalances {
  const balances = { ...entries };
  for (const asset in entries) {
    if (balances[asset].amount.isZero())
      delete balances[asset];
  }

  return balances;
}

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
    if (!acc[key]) {
      acc[key] = {
        ...breakdown,
        amount: Zero,
        value: Zero,
      } satisfies AssetBreakdown;
    }

    const balance = balanceSum(acc[key], breakdown);
    acc[key].amount = balance.amount;
    acc[key].value = balance.value;
    return acc;
  }, initial);

  return Object.values(grouped).sort((a, b) => sortDesc(a.value, b.value));
}

export function appendAssetBalance<T extends AssetBalance>(
  value: T,
  assets: Record<string, T>,
  getAssociatedAssetIdentifier: (identifier: string) => ComputedRef<string>,
): void {
  const identifier = getAssociatedAssetIdentifier(value.asset);
  const associatedAsset: string = get(identifier);
  const ownedAsset = assets[associatedAsset];
  if (!ownedAsset)
    assets[associatedAsset] = { ...value };
  else
    assets[associatedAsset] = { ...balanceSum(ownedAsset, value) };
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

export function sum(balances: { usdValue: BigNumber }[] | { value: BigNumber }[]): BigNumber {
  return bigNumberSum(balances.map(account => 'usdValue' in account ? account.usdValue : account.value));
}

export function balanceUsdValueSum(balances: HasBalance[]): BigNumber {
  return balances.reduce((sum, balance) => sum.plus(balance.balance.usdValue), Zero);
}

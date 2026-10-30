import type { DataTableSortData } from '@rotki/ui-library';
import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import type { PlainAssetInfoReturn } from '@/modules/assets/use-asset-info-retrieval';
import {
  type AssetBalance,
  type AssetBalanceWithPrice,
  type BigNumber,
  type ProtocolBalance,
  type Writeable,
  Zero,
} from '@rotki/common';
import { sortDesc } from '@/modules/core/common/data/bignumbers';
import { balanceSum, bigNumberSum } from '@/modules/core/common/data/calculation';
import { getSortItems } from '@/modules/core/common/display/assets';

export function groupAssetBreakdown(
  breakdowns: AssetBreakdown[],
  groupBy: (item: AssetBreakdown) => string = (item: AssetBreakdown) => item.location + item.address,
): AssetBreakdown[] {
  const initial: Record<string, Writeable<AssetBreakdown>> = {};
  const grouped = breakdowns.reduce((acc, breakdown) => {
    const key = groupBy(breakdown);
    const existing = acc[key];
    if (!existing) {
      acc[key] = { ...breakdown };
      return acc;
    }

    const balance = balanceSum(existing, breakdown);
    existing.amount = balance.amount;
    existing.value = balance.value;
    if (breakdown.awaitingClaim)
      existing.awaitingClaim = (existing.awaitingClaim ?? Zero).plus(breakdown.awaitingClaim);
    return acc;
  }, initial);

  return Object.values(grouped).sort((a, b) => sortDesc(a.value, b.value));
}

/** Whether part of the protocol balance is a withdrawal the user still has to claim. */
export function hasAwaitingClaim(balance: Pick<ProtocolBalance, 'awaitingClaim'>): boolean {
  return balance.awaitingClaim?.gt(0) ?? false;
}

export function sum(balances: readonly { value: BigNumber }[]): BigNumber {
  return bigNumberSum(balances.map(account => account.value));
}

/** The only columns `getSortItems` can order: asset by symbol, the other two as BigNumbers. */
const SORTABLE_ASSET_COLUMNS = ['amount', 'asset', 'value'] as const satisfies readonly (keyof AssetBalance)[];

export function sortAssetBalances<T extends AssetBalance = AssetBalanceWithPrice>(data: T[], sort: DataTableSortData<T>, getAssetInfo: PlainAssetInfoReturn): T[] {
  const sortItems = getSortItems<T>(asset => getAssetInfo(asset));

  const sortBy = get(sort);
  if (Array.isArray(sortBy) || !sortBy?.column)
    return data;

  const column = SORTABLE_ASSET_COLUMNS.find(candidate => candidate === sortBy.column);
  if (!column)
    return data;

  return sortItems(data, [column], [sortBy.direction === 'desc']);
}

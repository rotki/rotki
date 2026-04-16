import type {
  AssetBalance,
  AssetBalanceWithPrice,
  BigNumber,
  Writeable,
} from '@rotki/common';
import type { DataTableSortData } from '@rotki/ui-library';
import type { AssetBreakdown } from '@/modules/accounts/blockchain-accounts';
import type { PlainAssetInfoReturn } from '@/modules/assets/use-asset-info-retrieval';
import { sortDesc, zeroBalance } from '@/modules/core/common/data/bignumbers';
import { balanceSum, bigNumberSum } from '@/modules/core/common/data/calculation';
import { getSortItems } from '@/modules/core/common/display/assets';

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
    acc[key].value = balance.value;
    return acc;
  }, initial);

  return Object.values(grouped).sort((a, b) => sortDesc(a.value, b.value));
}

export function sum(balances: { value: BigNumber }[]): BigNumber {
  return bigNumberSum(balances.map(account => account.value));
}

export function sortAssetBalances<T extends AssetBalance = AssetBalanceWithPrice>(data: T[], sort: DataTableSortData<T>, getAssetInfo: PlainAssetInfoReturn): T[] {
  const sortItems = getSortItems<T>(asset => getAssetInfo(asset));

  const sortBy = get(sort);
  if (!Array.isArray(sortBy) && sortBy?.column)
    return sortItems(data, [sortBy.column as keyof AssetBalance], [sortBy.direction === 'desc']);

  return data;
}

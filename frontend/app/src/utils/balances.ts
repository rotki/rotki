import type {
  AssetBalance,
  AssetBalanceWithPrice,
  BigNumber,
  Writeable,
} from '@rotki/common';
import type { DataTableSortData } from '@rotki/ui-library';
import type { AssetInfoReturn } from '@/composables/assets/retrieval';
import type { AssetBreakdown } from '@/types/blockchain/accounts';
import { getSortItems } from '@/utils/assets';
import { sortDesc, zeroBalance } from '@/utils/bignumbers';
import { balanceSum, bigNumberSum } from '@/utils/calculation';

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

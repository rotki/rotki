import type { AssetBalance, AssetBalanceWithPrice, BigNumber, Nullable } from '@rotki/common';
import type { DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { bigNumberSum, calculatePercentage } from '@/modules/core/common/data/calculation';
import { assetFilterByKeyword } from '@/modules/core/common/display/assets';
import { sortAssetBalances } from '@/modules/core/common/display/balances';
import { useDashboardStores } from '@/modules/dashboard/use-dashboard-stores';

interface UseDashboardAssetDataReturn {
  isAssetMissing: (item: AssetBalanceWithPrice) => boolean;
  percentageOfCurrentGroup: (item: AssetBalanceWithPrice) => string;
  percentageOfTotalNetValue: (item: AssetBalanceWithPrice) => string;
  search: Ref<string>;
  sorted: ComputedRef<AssetBalanceWithPrice[]>;
  total: ComputedRef<BigNumber>;
}

export function useDashboardAssetData(
  balances: MaybeRefOrGetter<AssetBalanceWithPrice[]>,
  sort: MaybeRefOrGetter<DataTableSortData<AssetBalanceWithPrice>>,
): UseDashboardAssetDataReturn {
  const search = shallowRef<string>('');
  const debouncedSearch = refDebounced(search, 200);

  const { totalNetWorth } = useDashboardStores();
  const { getAssetInfo } = useAssetSelectInfo();
  const { missingCustomAssets } = useManualBalanceData();

  function assetFilter(item: Nullable<AssetBalance>): boolean {
    return assetFilterByKeyword(item, get(debouncedSearch), getAssetInfo);
  }

  function isAssetMissing(item: AssetBalanceWithPrice): boolean {
    return get(missingCustomAssets).includes(item.asset);
  }

  const total = computed<BigNumber>(() => bigNumberSum(toValue(balances).map(b => b.value)));

  function percentageOfTotalNetValue({ value }: AssetBalanceWithPrice): string {
    const netWorth = get(totalNetWorth);
    const totalWorth = netWorth.lt(0) ? get(total) : netWorth;
    return calculatePercentage(value, totalWorth);
  }

  function percentageOfCurrentGroup({ value }: AssetBalanceWithPrice): string {
    return calculatePercentage(value, get(total));
  }

  const sorted = computed<AssetBalanceWithPrice[]>(() => {
    const filteredBalances = toValue(balances).filter(assetFilter);
    return sortAssetBalances(filteredBalances, toValue(sort), getAssetInfo);
  });

  return {
    isAssetMissing,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    search,
    sorted,
    total,
  };
}

import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { useAssetBalanceSearch } from '@/modules/assets/use-asset-balance-search';
import { useAssetSelectInfo } from '@/modules/assets/use-asset-select-info';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { bigNumberSum, calculatePercentage } from '@/modules/core/common/data/calculation';
import { sortAssetBalances } from '@/modules/core/common/display/balances';
import { useDashboardStores } from '@/modules/dashboard/use-dashboard-stores';

interface UseDashboardAssetDataReturn {
  isAssetMissing: (item: AssetBalanceWithPrice) => boolean;
  percentageOfCurrentGroup: (item: AssetBalanceWithPrice) => string;
  percentageOfTotalNetValue: (item: AssetBalanceWithPrice) => string;
  modelSearch: Ref<string>;
  sorted: ComputedRef<AssetBalanceWithPrice[]>;
  total: ComputedRef<BigNumber>;
}

export function useDashboardAssetData(
  balances: MaybeRefOrGetter<AssetBalanceWithPrice[]>,
  sort: MaybeRefOrGetter<DataTableSortData<AssetBalanceWithPrice>>,
): UseDashboardAssetDataReturn {
  const modelSearch = shallowRef<string>('');
  const debouncedSearch = refDebounced(modelSearch, 200);

  const { totalNetWorth } = useDashboardStores();
  const { getAssetInfo } = useAssetSelectInfo();
  const { missingCustomAssets } = useManualBalanceData();
  const { matches, prioritizeExactMatches } = useAssetBalanceSearch(balances, debouncedSearch);

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

  const sorted = computed<AssetBalanceWithPrice[]>(() =>
    prioritizeExactMatches(sortAssetBalances([...get(matches)], toValue(sort), getAssetInfo)));

  return {
    isAssetMissing,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    modelSearch,
    sorted,
    total,
  };
}

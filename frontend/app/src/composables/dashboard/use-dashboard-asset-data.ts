import type { DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import { type AssetBalance, type AssetBalanceWithPrice, type BigNumber, type Nullable, Zero } from '@rotki/common';
import { useAssetSelectInfo } from '@/composables/assets/asset-select-info';
import { useDashboardStores } from '@/composables/dashboard/use-dashboard-stores';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { assetFilterByKeyword } from '@/utils/assets';
import { sortAssetBalances } from '@/utils/balances';
import { aggregateTotal, calculatePercentage } from '@/utils/calculation';

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
  const search = ref<string>('');
  const debouncedSearch = debouncedRef(search, 200);

  const { currencySymbol, totalNetWorth } = useDashboardStores();
  const { useExchangeRate } = usePriceUtils();
  const { assetInfo, assetName, assetSymbol } = useAssetSelectInfo();
  const { missingCustomAssets } = useManualBalanceData();

  function assetFilter(item: Nullable<AssetBalance>): boolean {
    return assetFilterByKeyword(item, get(debouncedSearch), assetName, assetSymbol);
  }

  function isAssetMissing(item: AssetBalanceWithPrice): boolean {
    return get(missingCustomAssets).includes(item.asset);
  }

  const total = computed<BigNumber>(() => {
    const currency = get(currencySymbol);
    const rate = get(useExchangeRate(currency)) ?? Zero;
    return aggregateTotal(toValue(balances), currency, rate);
  });

  function percentageOfTotalNetValue({ amount, asset, usdValue }: AssetBalanceWithPrice): string {
    const currency = get(currencySymbol);
    const netWorth = get(totalNetWorth);
    const rate = get(useExchangeRate(currency)) ?? Zero;
    const value = currency === asset ? amount : usdValue.multipliedBy(rate);
    const totalWorth = netWorth.lt(0) ? get(total) : netWorth;
    return calculatePercentage(value, totalWorth);
  }

  function percentageOfCurrentGroup({ amount, asset, usdValue }: AssetBalanceWithPrice): string {
    const currency = get(currencySymbol);
    const rate = get(useExchangeRate(currency)) ?? Zero;
    const value = currency === asset ? amount : usdValue.multipliedBy(rate);
    return calculatePercentage(value, get(total));
  }

  const sorted = computed<AssetBalanceWithPrice[]>(() => {
    const filteredBalances = toValue(balances).filter(assetFilter);
    return sortAssetBalances(filteredBalances, toValue(sort), assetInfo);
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

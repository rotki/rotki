import type { ComputedRef } from 'vue';
import type { BalanceByLocation, LocationBalance } from '@/types/balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { sortDesc } from '@/utils/bignumbers';
import { uniqueStrings } from '@/utils/data';

interface UseManualBalanceDataReturn {
  manualBalanceByLocation: ComputedRef<LocationBalance[]>;
  manualLabels: ComputedRef<string[]>;
  manualBalancesAssets: ComputedRef<string[]>;
  missingCustomAssets: ComputedRef<string[]>;
}

export function useManualBalanceData(): UseManualBalanceDataReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { useExchangeRate } = usePriceUtils();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  const manualLabels = computed<string[]>(() => {
    const labels: string[] = [];
    for (const balance of get(manualBalances)) {
      labels.push(balance.label);
    }

    for (const balance of get(manualLiabilities)) {
      labels.push(balance.label);
    }
    return labels;
  });

  const manualBalancesAssets = computed<string[]>(() => {
    const assets: string[] = [];
    for (const balance of get(manualBalances)) {
      assets.push(balance.asset);
    }

    for (const balance of get(manualLiabilities)) {
      assets.push(balance.asset);
    }
    return assets.filter(uniqueStrings);
  });

  const missingCustomAssets = computed<string[]>(() => {
    const missingAssets: string[] = [];
    for (const balance of get(manualBalances)) {
      if (balance.assetIsMissing) {
        missingAssets.push(balance.asset);
      }
    }

    for (const balance of get(manualLiabilities)) {
      if (balance.assetIsMissing) {
        missingAssets.push(balance.asset);
      }
    }
    return missingAssets;
  });

  const manualBalanceByLocation = computed<LocationBalance[]>(() => {
    const mainCurrency = get(currencySymbol);
    const balances = get(manualBalances);
    const currentExchangeRate = get(useExchangeRate(mainCurrency));
    if (currentExchangeRate === undefined)
      return [];

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: BalanceByLocation = balances.reduce(
      (result: BalanceByLocation, manualBalance: LocationBalance) => {
        if (result[manualBalance.location]) {
          // if the location exists on the reduced object, add the `value` of the current item to the previous total
          result[manualBalance.location] = result[manualBalance.location].plus(manualBalance.value);
        }
        else {
          // otherwise create the location and initiate its value
          result[manualBalance.location] = manualBalance.value;
        }

        return result;
      },
      {},
    );

    return Object.keys(aggregateManualBalancesByLocation)
      .map(location => ({
        location,
        value: aggregateManualBalancesByLocation[location],
      }))
      .sort((a, b) => sortDesc(a.value, b.value));
  });

  return {
    manualBalanceByLocation,
    manualBalancesAssets,
    manualLabels,
    missingCustomAssets,
  };
}

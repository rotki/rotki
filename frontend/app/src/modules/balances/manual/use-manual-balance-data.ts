import type { BalanceByLocation, LocationBalance } from '@/types/balances';
import type { BigNumber } from '@rotki/common';
import type { ComputedRef } from 'vue';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { sortDesc } from '@/utils/bignumbers';

interface UseManualBalanceDataReturn {
  manualBalanceByLocation: ComputedRef<LocationBalance[]>;
  manualLabels: ComputedRef<string[]>;
  missingCustomAssets: ComputedRef<string[]>;
}

export function useManualBalanceData(): UseManualBalanceDataReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { exchangeRate } = useBalancePricesStore();
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
    const currentExchangeRate = get(exchangeRate(mainCurrency));
    if (currentExchangeRate === undefined)
      return [];

    const simplifyManualBalances = balances.map((perLocationBalance) => {
      // because we mix different assets we need to convert them before they are aggregated
      // thus in amount display we always pass the manualBalanceByLocation in the user's main currency
      let convertedValue: BigNumber;
      if (mainCurrency === perLocationBalance.asset)
        convertedValue = perLocationBalance.amount;
      else convertedValue = perLocationBalance.usdValue.multipliedBy(currentExchangeRate);

      // to avoid double-conversion, we take as usdValue the amount property when the original asset type and
      // user's main currency coincide
      const { location, usdValue }: LocationBalance = {
        location: perLocationBalance.location,
        usdValue: convertedValue,
      };
      return { location, usdValue };
    });

    // Aggregate all balances per location
    const aggregateManualBalancesByLocation: BalanceByLocation = simplifyManualBalances.reduce(
      (result: BalanceByLocation, manualBalance: LocationBalance) => {
        if (result[manualBalance.location]) {
          // if the location exists on the reduced object, add the usdValue of the current item to the previous total
          result[manualBalance.location] = result[manualBalance.location].plus(manualBalance.usdValue);
        }
        else {
          // otherwise create the location and initiate its value
          result[manualBalance.location] = manualBalance.usdValue;
        }

        return result;
      },
      {},
    );

    return Object.keys(aggregateManualBalancesByLocation)
      .map(location => ({
        location,
        usdValue: aggregateManualBalancesByLocation[location],
      }))
      .sort((a, b) => sortDesc(a.usdValue, b.usdValue));
  });

  return {
    manualBalanceByLocation,
    manualLabels,
    missingCustomAssets,
  };
}

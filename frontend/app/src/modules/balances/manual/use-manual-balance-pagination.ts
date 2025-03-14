import type { Collection } from '@/types/collection';
import type { ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/types/manual-balances';
import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBalancePricesStore } from '@/store/balances/prices';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { sortAndFilterManualBalance } from '@/utils/balances/manual/manual-balances';

interface UseManualBalancePaginationReturn {
  fetchBalances: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
  fetchLiabilities: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
}

export function useManualBalancePagination(): UseManualBalancePaginationReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { assetPrice, exchangeRate, isAssetPriceInCurrentCurrency } = useBalancePricesStore();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  const resolvers: {
    resolveAssetPrice: (asset: string) => BigNumber | undefined;
  } = {
    /**
     * Resolves the asset price in the selected currency.
     * We use this to make sure that total is not affected by double conversion problems.
     *
     * @param asset The asset for which we want the price
     */
    resolveAssetPrice(asset: string): BigNumber | undefined {
      const inCurrentCurrency = get(isAssetPriceInCurrentCurrency(asset));
      const price = get(assetPrice(asset));
      if (!price)
        return undefined;

      if (inCurrentCurrency)
        return price;

      const currentExchangeRate = get(exchangeRate(get(currencySymbol)));

      if (!currentExchangeRate)
        return price;

      return price.times(currentExchangeRate);
    },
  };

  const fetchLiabilities = async (
    payload: MaybeRef<ManualBalanceRequestPayload>,
  ): Promise<Collection<ManualBalanceWithPrice>> =>
    Promise.resolve(sortAndFilterManualBalance(get(manualLiabilities), get(payload), resolvers));

  const fetchBalances = async (payload: MaybeRef<ManualBalanceRequestPayload>): Promise<Collection<ManualBalanceWithPrice>> =>
    Promise.resolve(sortAndFilterManualBalance(get(manualBalances), get(payload), resolvers));

  return {
    fetchBalances,
    fetchLiabilities,
  };
}

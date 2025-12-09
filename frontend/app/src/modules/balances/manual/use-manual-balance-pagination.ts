import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from '@vueuse/core';
import type { Collection } from '@/types/collection';
import type { ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/types/manual-balances';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { sortAndFilterManualBalance } from '@/utils/balances/manual/manual-balances';

interface UseManualBalancePaginationReturn {
  fetchBalances: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
  fetchLiabilities: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
}

export function useManualBalancePagination(): UseManualBalancePaginationReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { assetPriceInCurrentCurrency } = usePriceUtils();

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
      return get(assetPriceInCurrentCurrency(asset));
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

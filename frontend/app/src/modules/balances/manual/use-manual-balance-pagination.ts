import type { BigNumber } from '@rotki/common';
import type { MaybeRef } from 'vue';
import type { ManualBalanceRequestPayload, ManualBalanceWithPrice } from '@/modules/balances/types/manual-balances';
import type { Collection } from '@/modules/common/collection';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { usePriceUtils } from '@/modules/prices/use-price-utils';
import { sortAndFilterManualBalance } from '@/utils/balances/manual/manual-balances';

interface UseManualBalancePaginationReturn {
  fetchBalances: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
  fetchLiabilities: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
}

export function useManualBalancePagination(): UseManualBalancePaginationReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { getAssetPrice } = usePriceUtils();

  const resolvers: {
    resolveAssetPrice: (asset: string) => BigNumber | undefined;
  } = {
    resolveAssetPrice(asset: string): BigNumber | undefined {
      return getAssetPrice(asset);
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

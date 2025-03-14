import type { Collection } from '@/types/collection';
import type {
  ManualBalanceRequestPayload,
  ManualBalanceWithPrice,
  ManualBalanceWithValue,
} from '@/types/manual-balances';
import type { MaybeRef } from '@vueuse/core';
import type { ComputedRef, Ref } from 'vue';
import { useManualBalancePagination } from '@/modules/balances/manual/use-manual-balance-pagination';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { uniqueStrings } from '@/utils/data';

interface UseManualBalancesOrLiabilitiesReturn {
  dataSource: ComputedRef<ManualBalanceWithValue[]>;
  fetch: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
  locations: ComputedRef<string[]>;
}

export function useManualBalancesOrLiabilities(
  type: Ref<'liabilities' | 'balances'>,
): UseManualBalancesOrLiabilitiesReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { fetchBalances, fetchLiabilities } = useManualBalancePagination();
  const dataSource = computed<ManualBalanceWithValue[]>(() => (get(type) === 'liabilities' ? get(manualLiabilities) : get(manualBalances)));

  const locations = computed<string[]>(() => [
    ...get(manualBalances).map(item => item.location),
    ...get(manualLiabilities).map(item => item.location),
  ].filter(uniqueStrings));

  const fetch = async (
    payload: MaybeRef<ManualBalanceRequestPayload>,
  ): Promise<Collection<ManualBalanceWithPrice>> => get(type) === 'liabilities' ? fetchLiabilities(payload) : fetchBalances(payload);

  return {
    dataSource,
    fetch,
    locations,
  };
}

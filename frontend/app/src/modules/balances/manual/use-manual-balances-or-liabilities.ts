import type { ComputedRef, MaybeRef, MaybeRefOrGetter } from 'vue';
import type {
  ManualBalanceRequestPayload,
  ManualBalanceWithPrice,
  ManualBalanceWithValue,
} from '@/modules/balances/types/manual-balances';
import type { Collection } from '@/modules/common/collection';
import { useManualBalancePagination } from '@/modules/balances/manual/use-manual-balance-pagination';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { uniqueStrings } from '@/utils/data';

interface UseManualBalancesOrLiabilitiesReturn {
  dataSource: ComputedRef<ManualBalanceWithValue[]>;
  fetch: (payload: MaybeRef<ManualBalanceRequestPayload>) => Promise<Collection<ManualBalanceWithPrice>>;
  locations: ComputedRef<string[]>;
}

export function useManualBalancesOrLiabilities(
  type: MaybeRefOrGetter<'liabilities' | 'balances'>,
): UseManualBalancesOrLiabilitiesReturn {
  const { manualBalances, manualLiabilities } = storeToRefs(useBalancesStore());
  const { fetchBalances, fetchLiabilities } = useManualBalancePagination();
  const dataSource = computed<ManualBalanceWithValue[]>(() => (toValue(type) === 'liabilities' ? get(manualLiabilities) : get(manualBalances)));

  const locations = computed<string[]>(() => [
    ...get(manualBalances).map(item => item.location),
    ...get(manualLiabilities).map(item => item.location),
  ].filter(uniqueStrings));

  const fetch = async (
    payload: MaybeRef<ManualBalanceRequestPayload>,
  ): Promise<Collection<ManualBalanceWithPrice>> => toValue(type) === 'liabilities' ? fetchLiabilities(payload) : fetchBalances(payload);

  return {
    dataSource,
    fetch,
    locations,
  };
}

import type { ResultAsync } from 'plainfp/result-async';
import type {
  ManualBalanceRequestPayload,
  ManualBalanceWithPrice,
  ManualBalanceWithValue,
} from '@/modules/balances/types/manual-balances';
import type { Collection } from '@/modules/core/common/collection';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRef, type MaybeRefOrGetter, toValue } from 'vue';
import { useManualBalancePagination } from '@/modules/balances/manual/use-manual-balance-pagination';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { uniqueStrings } from '@/modules/core/common/data/data';

interface UseManualBalancesOrLiabilitiesReturn {
  dataSource: ComputedRef<ManualBalanceWithValue[]>;
  fetch: (payload: MaybeRef<ManualBalanceRequestPayload>) => ResultAsync<Collection<ManualBalanceWithPrice>, never>;
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
  ): ResultAsync<Collection<ManualBalanceWithPrice>, never> => toValue(type) === 'liabilities' ? fetchLiabilities(payload) : fetchBalances(payload);

  return {
    dataSource,
    fetch,
    locations,
  };
}

import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { useStatisticsStore } from '@/store/statistics';
import { useStatusStore } from '@/store/status';
import { Section } from '@/types/status';
import { calculatePercentage } from '@/utils/calculation';
import { getCollectionData } from '@/utils/collection';

interface UseNftDataReturn {
  data: ComputedRef<NonFungibleBalance[]>;
  fetchData: () => Promise<void>;
  isLoading: Ref<boolean>;
  loading: ComputedRef<boolean>;
  pagination: any;
  percentageOfCurrentGroup: (value: BigNumber) => string;
  percentageOfTotalNetValue: (value: BigNumber) => string;
  refreshNonFungibleBalances: (force?: boolean) => Promise<void>;
  totalValue: ComputedRef<BigNumber | undefined | null>;
}

export function useNftData(): UseNftDataReturn {
  const ignoredAssetsHandling: IgnoredAssetsHandlingType = 'exclude';
  const extraParams = computed(() => ({ ignoredAssetsHandling }));

  const statistics = useStatisticsStore();
  const { totalNetWorthUsd } = storeToRefs(statistics);
  const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNftBalances();

  const {
    fetchData,
    isLoading,
    pagination,
    state: balances,
  } = usePaginationFilters<
    NonFungibleBalance,
    NonFungibleBalancesRequestPayload
  >(fetchNonFungibleBalances, {
    defaultSortBy: [{
      column: 'price',
      direction: 'desc',
    }],
    extraParams,
  });

  const { isLoading: isSectionLoading } = useStatusStore();
  const loading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);
  const { data, totalValue } = getCollectionData<NonFungibleBalance>(balances);

  function percentageOfTotalNetValue(value: BigNumber): string {
    return calculatePercentage(value, get(totalNetWorthUsd));
  }

  function percentageOfCurrentGroup(value: BigNumber): string {
    return calculatePercentage(value, get(totalValue) as BigNumber);
  }

  return {
    data,
    fetchData,
    isLoading,
    loading,
    pagination,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    refreshNonFungibleBalances,
    totalValue,
  };
}

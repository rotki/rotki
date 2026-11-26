import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import { type BigNumber, Zero } from '@rotki/common';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { type ComputedRef, type Ref, shallowRef, watch, type WritableComputedRef } from 'vue';
import { type IgnoredAssetsHandlingType, isIgnoredAssetsHandling } from '@/modules/assets/types';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { useNftColumns } from '@/modules/balances/non-fungible/use-nft-columns';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import { enumParam, refParams } from '@/modules/core/table/param-refs';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseNftDataOptions {
  /**
   * Switches to the dashboard widget variant: pagination state is kept outside the router query, the columns follow the
   * dashboard visible-column setting, and the reset-to-page-one watcher on the ignored assets filter is skipped.
   */
  dashboard?: boolean;
}

interface UseNftDataReturn {
  balances: Ref<Collection<NonFungibleBalance>>;
  cols: ComputedRef<DataTableColumn<NonFungibleBalance>[]>;
  currencySymbol: Readonly<Ref<string>>;
  data: ComputedRef<NonFungibleBalance[]>;
  dataLoading: Ref<boolean>;
  /** The last fetch failure, so the table can name it in place of its empty text. */
  error: Ref<unknown>;
  fetchData: () => Promise<void>;
  /** Entries matching the current filter, across all pages. Zero means there is nothing to show. */
  found: ComputedRef<number>;
  modelIgnoredAssetsHandling: Ref<IgnoredAssetsHandlingType>;
  pagination: WritableComputedRef<TablePaginationData>;
  percentageOfCurrentGroup: (value: BigNumber) => string;
  percentageOfTotalNetValue: (value: BigNumber) => string;
  refreshNonFungibleBalances: (ignoreCache?: boolean) => Promise<void>;
  sectionLoading: ComputedRef<boolean>;
  sort: WritableComputedRef<DataTableSortData<NonFungibleBalance>>;
  totalValue: ComputedRef<BigNumber | undefined | null>;
}

export function useNftData(options: UseNftDataOptions = {}): UseNftDataReturn {
  const { dashboard = false } = options;

  const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNftBalances();
  const currencySymbol = useSetting('currencySymbol');

  const modelIgnoredAssetsHandling = shallowRef<IgnoredAssetsHandlingType>('exclude');

  const { useIsActive } = useTaskCenter();
  const sectionLoading = useIsActive(ActivityKind.NFT_BALANCES);

  const {
    collection: balances,
    error,
    isLoading: dataLoading,
    pagination,
    refetch: fetchData,
    setPage,
    sort,
  } = useServerTable<
    NonFungibleBalance,
    NonFungibleBalancesRequestPayload
  >({
    fetch: fetchNonFungibleBalances,
    params: [refParams({
      ignoredAssetsHandling: enumParam(modelIgnoredAssetsHandling, isIgnoredAssetsHandling, 'exclude'),
    }, { to: 'both' })],
    sort: {
      default: {
        column: 'price',
        direction: 'desc',
      },
    },
    urlState: routeWhen(() => !dashboard),
  });

  const { data, found, totalValue } = getCollectionData(balances);

  // Watch ignoredAssetsHandling changes and reset to page 1 (only for non-dashboard)
  if (!dashboard) {
    watch(modelIgnoredAssetsHandling, () => {
      setPage(1);
    });
  }

  // Dashboard-specific: percentage calculations
  const statistics = useStatisticsStore();
  const { totalNetWorth } = storeToRefs(statistics);

  function percentageOfTotalNetValue(value: BigNumber): string {
    return calculatePercentage(value, get(totalNetWorth));
  }

  function percentageOfCurrentGroup(value: BigNumber): string {
    return calculatePercentage(value, get(totalValue) ?? Zero);
  }

  const cols = useNftColumns(dashboard);

  useRememberTableSorting<NonFungibleBalance>(TableId.NON_FUNGIBLE_BALANCES, sort, cols);

  return {
    balances,
    cols,
    currencySymbol,
    data,
    dataLoading,
    error,
    fetchData,
    found,
    modelIgnoredAssetsHandling,
    pagination,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    refreshNonFungibleBalances,
    sectionLoading,
    sort,
    totalValue,
  };
}

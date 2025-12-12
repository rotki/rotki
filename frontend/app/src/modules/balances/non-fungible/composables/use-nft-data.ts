import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { Collection } from '@/types/collection';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/types/nfbalances';
import { usePaginationFilters } from '@/composables/use-pagination-filter';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useStatisticsStore } from '@/store/statistics';
import { useStatusStore } from '@/store/status';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { Section } from '@/types/status';
import { TableColumn } from '@/types/table-column';
import { calculatePercentage } from '@/utils/calculation';
import { getCollectionData } from '@/utils/collection';

interface UseNftDataOptions {
  dashboard?: boolean;
}

interface UseNftDataReturn {
  balances: Ref<Collection<NonFungibleBalance>>;
  cols: ComputedRef<DataTableColumn<NonFungibleBalance>[]>;
  currencySymbol: ComputedRef<string>;
  data: ComputedRef<NonFungibleBalance[]>;
  dataLoading: Ref<boolean>;
  fetchData: () => Promise<void>;
  ignoredAssetsHandling: Ref<IgnoredAssetsHandlingType>;
  pagination: ComputedRef<TablePaginationData>;
  percentageOfCurrentGroup: (value: BigNumber) => string;
  percentageOfTotalNetValue: (value: BigNumber) => string;
  refreshNonFungibleBalances: (ignoreCache?: boolean) => Promise<void>;
  sectionLoading: ComputedRef<boolean>;
  sort: ComputedRef<DataTableSortData<NonFungibleBalance>>;
  totalValue: ComputedRef<BigNumber | undefined | null>;
}

export function useNftData(options: UseNftDataOptions = {}): UseNftDataReturn {
  const { dashboard = false } = options;

  const { fetchNonFungibleBalances, refreshNonFungibleBalances } = useNftBalances();
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { t } = useI18n({ useScope: 'global' });

  const ignoredAssetsHandling = ref<IgnoredAssetsHandlingType>('exclude');

  const extraParams = computed(() => ({
    ignoredAssetsHandling: get(ignoredAssetsHandling),
  }));

  const { isLoading: isSectionLoading } = useStatusStore();
  const sectionLoading = isSectionLoading(Section.NON_FUNGIBLE_BALANCES);

  const {
    fetchData,
    isLoading: dataLoading,
    pagination,
    setPage,
    sort,
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
    history: dashboard ? 'external' : 'router',
    ...(!dashboard && {
      onUpdateFilters(query): void {
        set(ignoredAssetsHandling, query.ignoredAssetsHandling || 'exclude');
      },
    }),
  });

  const { data, totalValue } = getCollectionData(balances);

  // Watch ignoredAssetsHandling changes and reset to page 1 (only for non-dashboard)
  if (!dashboard) {
    watch(ignoredAssetsHandling, () => {
      setPage(1);
    });
  }

  // Dashboard-specific: percentage calculations
  const statistics = useStatisticsStore();
  const { totalNetWorth } = storeToRefs(statistics);
  const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());

  function percentageOfTotalNetValue(value: BigNumber): string {
    return calculatePercentage(value, get(totalNetWorth));
  }

  function percentageOfCurrentGroup(value: BigNumber): string {
    return calculatePercentage(value, get(totalValue) as BigNumber);
  }

  // Columns configuration
  const cols = computed<DataTableColumn<NonFungibleBalance>[]>(() => {
    if (dashboard) {
      const group = DashboardTableType.NFT;
      const visibleColumns = get(dashboardTablesVisibleColumns)[group];

      const headers: DataTableColumn<NonFungibleBalance>[] = [{
        cellClass: 'py-0',
        class: 'text-no-wrap w-full',
        key: 'name',
        label: t('common.name'),
        sortable: true,
      }, {
        align: 'end',
        cellClass: 'py-0',
        class: 'text-no-wrap',
        key: 'priceInAsset',
        label: t('nft_balance_table.column.price_in_asset'),
      }, {
        align: 'end',
        cellClass: 'py-0',
        class: 'text-no-wrap',
        key: 'price',
        label: t('common.price_in_symbol', {
          symbol: get(currencySymbol),
        }),
        sortable: true,
      }];

      if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
        headers.push({
          align: 'end',
          cellClass: 'py-0',
          class: 'text-no-wrap',
          key: 'percentageOfTotalNetValue',
          label: t('nft_balance_table.column.percentage'),
        });
      }

      if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
        headers.push({
          align: 'end',
          cellClass: 'py-0',
          class: 'text-no-wrap',
          key: 'percentageOfTotalCurrentGroup',
          label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
            group,
          }),
        });
      }

      return headers;
    }

    // Non-dashboard columns
    return [{
      cellClass: 'text-no-wrap',
      key: 'name',
      label: t('common.name'),
      sortable: true,
    }, {
      align: 'center',
      key: 'ignored',
      label: t('non_fungible_balances.ignore'),
    }, {
      align: 'end',
      class: 'text-no-wrap',
      key: 'priceInAsset',
      label: t('non_fungible_balances.column.price_in_asset'),
      width: '75%',
    }, {
      align: 'end',
      class: 'text-no-wrap',
      key: 'price',
      label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
      sortable: true,
    }, {
      class: 'text-no-wrap',
      key: 'manuallyInput',
      label: t('non_fungible_balances.column.custom_price'),
    }, {
      align: 'center',
      key: 'actions',
      label: t('common.actions_text'),
      width: '50',
    }];
  });

  useRememberTableSorting<NonFungibleBalance>(TableId.NON_FUNGIBLE_BALANCES, sort, cols);

  return {
    balances,
    cols,
    currencySymbol,
    data,
    dataLoading,
    fetchData,
    ignoredAssetsHandling,
    pagination,
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    refreshNonFungibleBalances,
    sectionLoading,
    sort,
    totalValue,
  };
}

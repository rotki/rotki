import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { NonFungibleBalance, NonFungibleBalancesRequestPayload } from '@/modules/balances/types/nfbalances';
import type { Collection } from '@/modules/core/common/collection';
import { type BigNumber, Zero } from '@rotki/common';
import { useNftBalances } from '@/modules/balances/nft/use-nft-balances';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { getCollectionData } from '@/modules/core/common/data/collection-utils';
import { Section } from '@/modules/core/common/status';
import { TableColumn } from '@/modules/core/table/table-column';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { routeWhen, useServerTable } from '@/modules/core/table/use-server-table';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { useSectionStatus } from '@/modules/shell/sync-progress/use-section-status';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

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
  fetchData: () => Promise<void>;
  modelIgnoredAssetsHandling: Ref<IgnoredAssetsHandlingType>;
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
  const currencySymbol = useSetting('currencySymbol');
  const { t } = useI18n({ useScope: 'global' });

  const modelIgnoredAssetsHandling = shallowRef<IgnoredAssetsHandlingType>('exclude');

  const extraParams = computed<Record<string, unknown>>(() => ({
    ignoredAssetsHandling: get(modelIgnoredAssetsHandling),
  }));

  const { isLoading: sectionLoading } = useSectionStatus(Section.NON_FUNGIBLE_BALANCES);

  const {
    collection: balances,
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
    params: [{
      fromQuery(query): void {
        set(modelIgnoredAssetsHandling, query.ignoredAssetsHandling ?? 'exclude');
      },
      to: 'both',
      values: extraParams,
    }],
    sort: {
      default: [{
        column: 'price',
        direction: 'desc',
      }],
    },
    urlState: routeWhen(() => !dashboard),
  });

  const { data, totalValue } = getCollectionData(balances);

  // Watch ignoredAssetsHandling changes and reset to page 1 (only for non-dashboard)
  if (!dashboard) {
    watch(modelIgnoredAssetsHandling, () => {
      setPage(1);
    });
  }

  // Dashboard-specific: percentage calculations
  const statistics = useStatisticsStore();
  const { totalNetWorth } = storeToRefs(statistics);
  const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');

  function percentageOfTotalNetValue(value: BigNumber): string {
    return calculatePercentage(value, get(totalNetWorth));
  }

  function percentageOfCurrentGroup(value: BigNumber): string {
    return calculatePercentage(value, get(totalValue) ?? Zero);
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

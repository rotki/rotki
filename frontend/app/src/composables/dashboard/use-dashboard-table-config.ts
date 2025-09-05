import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { DashboardTableType } from '@/types/settings/frontend-settings';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { TableColumn } from '@/types/table-column';

interface UseDashboardTableConfigReturn {
  pagination: Ref<{ itemsPerPage: number; page: number }>;
  setPage: (page: number) => void;
  setTablePagination: (event: TablePaginationData | undefined) => void;
  sort: Ref<DataTableSortData<AssetBalanceWithPrice>>;
  tableHeaders: ComputedRef<DataTableColumn<AssetBalanceWithPrice>[]>;
}

export function useDashboardTableConfig(
  tableType: MaybeRefOrGetter<DashboardTableType>,
  title: MaybeRefOrGetter<string>,
  totalNetWorth: MaybeRefOrGetter<BigNumber>,
): UseDashboardTableConfigReturn {
  const { t } = useI18n({ useScope: 'global' });

  const sort = ref<DataTableSortData<AssetBalanceWithPrice>>({
    column: 'usdValue',
    direction: 'desc' as const,
  });

  const pagination = ref({
    itemsPerPage: 10,
    page: 1,
  });

  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());
  const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());

  function setPage(page: number): void {
    set(pagination, {
      ...get(pagination),
      page,
    });
  }

  function setTablePagination(event: TablePaginationData | undefined): void {
    if (!isDefined(event))
      return;

    const { limit, page } = event;
    set(pagination, {
      itemsPerPage: limit,
      page,
    });
  }

  const tableHeaders = computed<DataTableColumn<AssetBalanceWithPrice>[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[toValue(tableType)];

    const headers: DataTableColumn<AssetBalanceWithPrice>[] = [{
      cellClass: 'py-0',
      class: 'text-no-wrap w-full',
      key: 'asset',
      label: t('common.asset'),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap w-full',
      key: 'protocol',
      label: t('common.location'),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'usdPrice',
      label: t('common.price_in_symbol', {
        symbol: get(currencySymbol),
      }),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'py-0',
      key: 'amount',
      label: t('common.amount'),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'py-0',
      class: 'text-no-wrap',
      key: 'usdValue',
      label: t('common.value_in_symbol', {
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
        label: toValue(totalNetWorth).gt(0)
          ? t('dashboard_asset_table.headers.percentage_of_total_net_value')
          : t('dashboard_asset_table.headers.percentage_total'),
      });
    }

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
      headers.push({
        align: 'end',
        cellClass: 'py-0',
        class: 'text-no-wrap',
        key: 'percentageOfTotalCurrentGroup',
        label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
          group: toValue(title),
        }),
      });
    }

    return headers;
  });

  useRememberTableSorting<AssetBalanceWithPrice>(TableId.DASHBOARD_ASSET, sort, tableHeaders);

  return {
    pagination,
    setPage,
    setTablePagination,
    sort,
    tableHeaders,
  };
}

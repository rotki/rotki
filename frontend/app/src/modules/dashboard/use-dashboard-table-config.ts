import type { AssetBalanceWithPrice, BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData, TablePaginationData } from '@rotki/ui-library';
import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import type { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { useAssetBalanceColumns } from '@/modules/balances/use-asset-balance-columns';
import { TableColumn } from '@/modules/core/table/table-column';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useSetting } from '@/modules/settings/use-setting';

interface UseDashboardTableConfigReturn {
  pagination: DeepReadonly<Ref<{ itemsPerPage: number; page: number }>>;
  setPage: (page: number) => void;
  setTablePagination: (event: TablePaginationData | undefined) => void;
  modelSort: Ref<DataTableSortData<AssetBalanceWithPrice>>;
  tableHeaders: ComputedRef<DataTableColumn<AssetBalanceWithPrice>[]>;
}

/**
 * Columns, sorting and paging of a dashboard asset table.
 *
 * @param tableType - which table the visible-columns setting is read for
 * @param title - the table's title, used in the current-group percentage header
 * @param totalNetWorth - the base of the net value percentage
 * @param showComparison - add the per-asset difference between history and queried amounts, in both
 * views, so switching views never adds or removes a column
 */
export function useDashboardTableConfig(
  tableType: MaybeRefOrGetter<DashboardTableType>,
  title: MaybeRefOrGetter<string>,
  totalNetWorth: MaybeRefOrGetter<BigNumber>,
  showComparison: MaybeRefOrGetter<boolean> = false,
): UseDashboardTableConfigReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { percentageColumn, valueColumns } = useAssetBalanceColumns();

  const modelSort = ref<DataTableSortData<AssetBalanceWithPrice>>({
    column: 'value',
    direction: 'desc' as const,
  });

  const pagination = ref({
    itemsPerPage: 10,
    page: 1,
  });

  const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');

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
    }, ...valueColumns()];

    if (toValue(showComparison)) {
      headers.push({
        align: 'end',
        cellClass: 'py-0',
        class: 'text-no-wrap',
        key: 'comparison',
        label: t('balance_view.history_vs_queried'),
      });
    }

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push(percentageColumn('percentageOfTotalNetValue', toValue(totalNetWorth).gt(0)
        ? t('dashboard_asset_table.headers.percentage_of_total_net_value')
        : t('dashboard_asset_table.headers.percentage_total')));
    }

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
      headers.push(percentageColumn('percentageOfTotalCurrentGroup', t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: toValue(title),
      })));
    }

    return headers;
  });

  useRememberTableSorting<AssetBalanceWithPrice>(TableId.DASHBOARD_ASSET, modelSort, tableHeaders);

  return {
    pagination: readonly(pagination),
    setPage,
    setTablePagination,
    modelSort,
    tableHeaders,
  };
}

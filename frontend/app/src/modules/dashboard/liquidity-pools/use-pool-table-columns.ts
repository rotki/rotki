import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { PoolLiquidityBalance } from './types';
import { get } from '@vueuse/shared';
import { storeToRefs } from 'pinia';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, ref, toValue } from 'vue';
import { useI18n } from 'vue-i18n';
import { calculatePercentage } from '@/modules/core/common/data/calculation';
import { TableColumn } from '@/modules/core/table/table-column';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';
import { useStatisticsStore } from '@/modules/statistics/use-statistics-store';

interface UsePoolTableColumnsReturn {
  sort: Ref<DataTableSortData<PoolLiquidityBalance>>;
  tableHeaders: ComputedRef<DataTableColumn<PoolLiquidityBalance>[]>;
  percentageOfTotalNetValue: (value: BigNumber) => string;
  percentageOfCurrentGroup: (value: BigNumber) => string;
}

/**
 * Columns of the liquidity pool table: the visible headers, the remembered sorting, and the two
 * percentage columns.
 *
 * @param total - the summed value of every pool in the table
 */
export function usePoolTableColumns(total: MaybeRefOrGetter<BigNumber>): UsePoolTableColumnsReturn {
  /** Bound to the table with `v-model:sort`, so the component writes it as well. */
  const modelSort = ref<DataTableSortData<PoolLiquidityBalance>>({
    column: 'value',
    direction: 'desc' as const,
  });

  const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');
  const { totalNetWorth } = storeToRefs(useStatisticsStore());
  const { t } = useI18n({ useScope: 'global' });

  const tableHeaders = computed<DataTableColumn<PoolLiquidityBalance>[]>(() => {
    const visibleColumns = get(dashboardTablesVisibleColumns)[DashboardTableType.LIQUIDITY_POSITION];

    const headers: DataTableColumn<PoolLiquidityBalance>[] = [{
      cellClass: 'text-no-wrap py-0',
      class: 'text-no-wrap w-full',
      key: 'name',
      label: t('common.name'),
    }, {
      align: 'end',
      cellClass: 'font-medium',
      class: 'text-no-wrap',
      key: 'value',
      label: t('common.value'),
      sortable: true,
    }];

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
      headers.push({
        align: 'end',
        cellClass: 'text-rui-text-secondary',
        class: 'text-no-wrap',
        key: 'percentageOfTotalNetValue',
        label: t('dashboard_asset_table.headers.percentage_of_total_net_value'),
      });
    }

    if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
      headers.push({
        align: 'end',
        cellClass: 'text-rui-text-secondary',
        class: 'text-no-wrap',
        key: 'percentageOfTotalCurrentGroup',
        label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
          group: t('modules.dashboard.liquidity_pools.pool_table.title'),
        }),
      });
    }

    return headers;
  });

  useRememberTableSorting<PoolLiquidityBalance>(TableId.POOL_LIQUIDITY_BALANCE, modelSort, tableHeaders);

  function percentageOfTotalNetValue(value: BigNumber): string {
    const netWorth = get(totalNetWorth);
    const totalVal = netWorth.lt(0) ? toValue(total) : netWorth;
    return calculatePercentage(value, totalVal);
  }

  function percentageOfCurrentGroup(value: BigNumber): string {
    return calculatePercentage(value, toValue(total));
  }

  return {
    percentageOfCurrentGroup,
    percentageOfTotalNetValue,
    sort: modelSort,
    tableHeaders,
  };
}

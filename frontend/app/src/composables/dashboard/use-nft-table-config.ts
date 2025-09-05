import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter, Ref } from 'vue';
import type { NonFungibleBalance } from '@/types/nfbalances';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { DashboardTableType } from '@/types/settings/frontend-settings';
import { TableColumn } from '@/types/table-column';

interface UseNftTableConfigReturn {
  sort: Ref<DataTableSortData<NonFungibleBalance>>;
  tableHeaders: ComputedRef<DataTableColumn<NonFungibleBalance>[]>;
}

export function useNftTableConfig(
  currencySymbol: MaybeRefOrGetter<string>,
): UseNftTableConfigReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { dashboardTablesVisibleColumns } = storeToRefs(useFrontendSettingsStore());

  const group = DashboardTableType.NFT;

  const sort = ref<DataTableSortData<NonFungibleBalance>>({
    column: 'usdPrice',
    direction: 'desc' as const,
  });

  const tableHeaders = computed<DataTableColumn<NonFungibleBalance>[]>(() => {
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
      key: 'usdPrice',
      label: t('common.price_in_symbol', {
        symbol: toValue(currencySymbol),
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
  });

  useRememberTableSorting<NonFungibleBalance>(TableId.NON_FUNGIBLE_BALANCES, sort, tableHeaders);

  return {
    sort,
    tableHeaders,
  };
}

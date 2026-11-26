import type { DataTableColumn } from '@rotki/ui-library';
import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef } from 'vue';
import { useI18n } from 'vue-i18n';
import { TableColumn } from '@/modules/core/table/table-column';
import { DashboardTableType } from '@/modules/settings/types/frontend-settings';
import { useSetting } from '@/modules/settings/use-setting';

/**
 * The columns of the NFT balances table.
 *
 * @remarks
 * The dashboard widget shows a compact set whose percentage columns follow the dashboard
 * visible-column setting; the balances page shows the full set, with the price labelled in the main
 * currency.
 *
 * @param dashboard - whether the columns are for the dashboard widget
 */
export function useNftColumns(dashboard: boolean): ComputedRef<DataTableColumn<NonFungibleBalance>[]> {
  const { t } = useI18n({ useScope: 'global' });
  const currencySymbol = useSetting('currencySymbol');
  const dashboardTablesVisibleColumns = useSetting('dashboardTablesVisibleColumns');

  return computed<DataTableColumn<NonFungibleBalance>[]>(() => {
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
        cellClass: 'py-0 text-rui-text-secondary',
        class: 'text-no-wrap',
        key: 'priceInAsset',
        label: t('nft_balance_table.column.price_in_asset'),
      }, {
        align: 'end',
        cellClass: 'py-0 font-medium',
        class: 'text-no-wrap',
        key: 'price',
        label: t('common.price'),
        sortable: true,
      }];

      if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE)) {
        headers.push({
          align: 'end',
          cellClass: 'py-0 text-rui-text-secondary',
          class: 'text-no-wrap',
          key: 'percentageOfTotalNetValue',
          label: t('nft_balance_table.column.percentage'),
        });
      }

      if (visibleColumns.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
        headers.push({
          align: 'end',
          cellClass: 'py-0 text-rui-text-secondary',
          class: 'text-no-wrap',
          key: 'percentageOfTotalCurrentGroup',
          label: t('dashboard_asset_table.headers.percentage_of_total_current_group', {
            group,
          }),
        });
      }

      return headers;
    }

    // Non-dashboard columns: as in the other balance tables, the asset price recedes and the main currency price leads
    return [{
      class: 'w-full',
      // max-w-0: the name takes what the other columns leave and truncates, rather than widening the table
      cellClass: 'text-no-wrap max-w-0',
      key: 'name',
      label: t('common.name'),
      sortable: true,
    }, {
      align: 'center',
      key: 'ignored',
      label: t('non_fungible_balances.ignore'),
    }, {
      align: 'end',
      cellClass: 'text-rui-text-secondary',
      class: 'text-no-wrap',
      key: 'priceInAsset',
      label: t('non_fungible_balances.column.price_in_asset'),
    }, {
      align: 'end',
      cellClass: 'font-medium',
      class: 'text-no-wrap',
      key: 'price',
      label: t('common.price_in_symbol', { symbol: get(currencySymbol) }),
      sortable: true,
    }, {
      align: 'center',
      class: 'text-no-wrap',
      key: 'manuallyInput',
      label: t('non_fungible_balances.column.custom_price'),
    }, {
      align: 'end',
      key: 'actions',
      label: t('common.actions_text'),
    }];
  });
}

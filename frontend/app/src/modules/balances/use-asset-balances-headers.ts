import type { AssetBalanceWithPrice } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AssetBalancesDisplay } from '@/modules/balances/types/balances';
import { useAssetBalanceColumns } from '@/modules/balances/use-asset-balance-columns';
import { TableColumn } from '@/modules/core/table/table-column';

type AssetBalanceColumn = DataTableColumn<AssetBalanceWithPrice>;

/**
 * Fixed widths, so panel tables stacked one under another keep their columns in line.
 *
 * @remarks
 * They only hold while the asset column is the one auto-width column: a `w-full` there claims the
 * spare width and the browser shrinks the fixed columns back to their content.
 */
const PANEL_COLUMN_WIDTHS: Record<string, string> = {
  amount: 'w-28',
  asset: '',
  perProtocol: 'w-20',
  price: 'w-28',
  value: 'w-32',
};

/** Columns a panel drops when the screen is too narrow for them, so Amount and Value stay in view. */
const NARROW_PANEL_DROPPED = new Set<string>(['perProtocol', 'price']);

/** The panel variant of the columns: fixed widths, and fewer of them on a narrow screen. */
function panelColumns(headers: AssetBalanceColumn[], narrow: boolean): AssetBalanceColumn[] {
  return headers
    .filter(header => !narrow || !NARROW_PANEL_DROPPED.has(String(header.key)))
    .map((header) => {
      const width = PANEL_COLUMN_WIDTHS[String(header.key)];
      if (width === undefined)
        return header;

      const rest = (header.class ?? '').split(' ').filter(name => name !== 'w-full');
      const shrinks = header.key === 'asset' ? { cellClass: [header.cellClass, 'max-w-0 overflow-hidden'].filter(Boolean).join(' ') } : {};
      return { ...header, ...shrinks, class: [...rest, width].filter(Boolean).join(' ') };
    });
}

/**
 * The columns of the balances pages' asset table.
 *
 * @param display - which optional columns to show
 * @param fillsPanel - whether the table fills a panel, which fixes the column widths
 */
export function useAssetBalancesHeaders(
  display: MaybeRefOrGetter<AssetBalancesDisplay | undefined>,
  fillsPanel: MaybeRefOrGetter<boolean>,
): ComputedRef<AssetBalanceColumn[]> {
  const { t } = useI18n({ useScope: 'global' });
  const { percentageColumn, valueColumns } = useAssetBalanceColumns();
  const { isMdAndDown } = useBreakpoint();

  return computed<AssetBalanceColumn[]>(() => {
    const options = toValue(display);
    const headers: AssetBalanceColumn[] = [{
      cellClass: 'py-0',
      class: 'text-no-wrap w-full',
      key: 'asset',
      label: t('common.asset'),
      sortable: true,
    }, ...valueColumns()];

    if (options?.showPerProtocol) {
      headers.splice(1, 0, {
        align: 'end',
        cellClass: 'py-0',
        class: 'text-no-wrap',
        key: 'perProtocol',
        label: t('common.location'),
        sortable: false,
      });
    }

    if (options?.visibleColumns?.includes(TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE))
      headers.push(percentageColumn('percentageOfTotalNetValue', t('dashboard_asset_table.headers.percentage_of_total_net_value')));

    if (options?.visibleColumns?.includes(TableColumn.PERCENTAGE_OF_TOTAL_CURRENT_GROUP)) {
      headers.push(percentageColumn('percentageOfTotalCurrentGroup', t('dashboard_asset_table.headers.percentage_of_total_current_group', {
        group: t('blockchain_balances.group_label'),
      })));
    }

    return toValue(fillsPanel) ? panelColumns(headers, get(isMdAndDown)) : headers;
  });
}

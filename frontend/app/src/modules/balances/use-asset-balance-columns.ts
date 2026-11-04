import type { AssetBalanceWithPrice } from '@rotki/common';
import type { DataTableColumn } from '@rotki/ui-library';

type AssetBalanceColumn = DataTableColumn<AssetBalanceWithPrice>;

type PercentageKey = 'percentageOfTotalNetValue' | 'percentageOfTotalCurrentGroup';

interface UseAssetBalanceColumnsReturn {
  /** Price, Amount and Value, in that order: the price recedes and the value leads. */
  valueColumns: () => AssetBalanceColumn[];
  /** A share-of-total column, labelled by the caller since the total it is a share of varies. */
  percentageColumn: (key: PercentageKey, label: string) => AssetBalanceColumn;
}

/** The columns the asset balance tables (dashboard and balances pages) have in common. */
export function useAssetBalanceColumns(): UseAssetBalanceColumnsReturn {
  const { t } = useI18n({ useScope: 'global' });

  function valueColumns(): AssetBalanceColumn[] {
    return [{
      align: 'end',
      cellClass: 'py-0 text-rui-text-secondary',
      class: 'text-no-wrap',
      key: 'price',
      label: t('common.price'),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'py-0',
      key: 'amount',
      label: t('common.amount'),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'py-0 font-medium',
      class: 'text-no-wrap',
      key: 'value',
      label: t('common.value'),
      sortable: true,
    }];
  }

  function percentageColumn(key: PercentageKey, label: string): AssetBalanceColumn {
    return {
      align: 'end',
      cellClass: 'py-0 text-rui-text-secondary',
      class: 'text-no-wrap',
      key,
      label,
    };
  }

  return {
    percentageColumn,
    valueColumns,
  };
}

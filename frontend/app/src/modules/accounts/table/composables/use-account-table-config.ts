import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { AccountDataRow } from '../types';
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import type { SupportedCurrency } from '@/types/currencies';
import { TableId, useRememberTableSorting } from '@/modules/table/use-remember-table-sorting';
import { useGeneralSettingsStore } from '@/store/settings/general';

interface UseAccountTableConfigReturn<T extends BlockchainAccountBalance> {
  createColumns: (group: 'evm' | 'xpub' | undefined, anyExpansion: boolean) => DataTableColumn<AccountDataRow<T>>[];
  currencySymbol: ComputedRef<SupportedCurrency>;
  initializeTableSorting: (sort: Ref<DataTableSortData<T>>, cols: ComputedRef<DataTableColumn<AccountDataRow<T>>[]>) => void;
}

export function useAccountTableConfig<
  T extends BlockchainAccountBalance,
>(): UseAccountTableConfigReturn<T> {
  const { t } = useI18n({ useScope: 'global' });
  const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

  function createColumns(
    group: 'evm' | 'xpub' | undefined,
    anyExpansion: boolean,
  ): DataTableColumn<AccountDataRow<T>>[] {
    const currency = { symbol: get(currencySymbol) };

    return [...(anyExpansion
      ? [{
          cellClass: '!py-0 !pr-0 !pl-3',
          class: '!py-0 !pr-0 !pl-3',
          key: 'expand',
          label: '',
          sortable: false,
        }]
      : []), ...(group
      ? [{
          cellClass: 'py-0 !px-3',
          class: '!px-3',
          key: 'label',
          label: t('common.account'),
          sortable: true,
        }]
      : []), ...(group !== 'xpub'
      ? [{
          cellClass: 'py-0 !pr-0',
          class: '!pr-0',
          key: 'chain',
          label: t('common.chain'),
          sortable: false,
        }]
      : []), ...(group === 'evm'
      ? [{
          cellClass: 'py-0',
          key: 'tags',
          label: t('common.tags'),
          sortable: false,
        }]
      : []), {
      align: 'end',
      cellClass: 'py-0 !pr-0 !pl-2',
      class: '!pr-0 !pl-2',
      key: 'assets',
      label: t('common.assets'),
    }, {
      align: 'end',
      cellClass: 'py-0',
      key: 'usdValue',
      label: t('account_balances.headers.usd_value', currency),
      sortable: true,
    }, {
      align: 'end',
      cellClass: '!p-0',
      key: 'actions',
      label: t('common.actions_text'),
    }];
  }

  function initializeTableSorting(
    sort: Ref<DataTableSortData<T>>,
    cols: ComputedRef<DataTableColumn<AccountDataRow<T>>[]>,
  ): void {
    useRememberTableSorting<AccountDataRow<T>>(TableId.ACCOUNT_BALANCES, sort, cols);
  }

  return {
    createColumns,
    currencySymbol,
    initializeTableSorting,
  };
}

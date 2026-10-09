import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';

interface UseAccountTableConfigReturn<T extends BlockchainAccountBalance> {
  createColumns: (group: 'evm' | 'xpub' | undefined, anyExpansion: boolean) => DataTableColumn<AccountDataRow<T>>[];
  initializeTableSorting: (sort: Ref<DataTableSortData<T>>, cols: ComputedRef<DataTableColumn<AccountDataRow<T>>[]>) => void;
}

export function useAccountTableConfig<
  T extends BlockchainAccountBalance,
>(): UseAccountTableConfigReturn<T> {
  const { t } = useI18n({ useScope: 'global' });

  function createColumns(
    group: 'evm' | 'xpub' | undefined,
    anyExpansion: boolean,
  ): DataTableColumn<AccountDataRow<T>>[] {
    return [...(anyExpansion
      ? [{
          cellClass: 'py-0! pr-0! pl-3!',
          class: 'py-0! pr-0! pl-3!',
          key: 'expand',
          label: '',
          sortable: false,
        }]
      : []), ...(group
      ? [{
          cellClass: 'py-0 px-3!',
          // the account takes the auto layout's spare width, so the columns after it sit together
          class: 'px-3! w-full',
          key: 'label',
          label: t('common.account'),
          sortable: true,
        }]
      : []), ...(group !== 'xpub'
      ? [{
          cellClass: 'py-0 pr-0!',
          // without an account column, the chain column takes the auto layout's spare width
          class: group ? 'pr-0!' : 'pr-0! w-full',
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
      cellClass: 'py-0 pr-0! pl-2!',
      class: 'pr-0! pl-2!',
      key: 'assets',
      label: t('common.assets'),
    }, {
      align: 'end',
      cellClass: 'py-0',
      key: 'value',
      // the cells carry the currency symbol, so the header leaves it out
      label: t('common.value'),
      sortable: true,
    }, {
      align: 'end',
      cellClass: 'p-0!',
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
    initializeTableSorting,
  };
}

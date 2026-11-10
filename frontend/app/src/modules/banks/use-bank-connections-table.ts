import type { DataTableColumn, DataTableSortColumn } from '@rotki/ui-library';
import type { ComputedRef, Ref } from 'vue';
import type { BankConnection, BankConnectionIdentity } from '@/modules/banks/types';
import type { NamedFailure } from '@/modules/shell/components/named-failure';
import { type BigNumber, Zero } from '@rotki/common';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { connectionKey } from '@/modules/banks/bank-balances';
import { exchangeAssetSum } from '@/modules/core/common/data/calculation';
import { TableId, useRememberTableSorting } from '@/modules/core/table/use-remember-table-sorting';
import { useRowHighlight } from '@/modules/core/table/use-row-highlight';
import { useTableRowDeletion } from '@/modules/core/table/use-table-row-deletion';

interface UseBankConnectionsTableReturn {
  cols: ComputedRef<DataTableColumn<BankConnection>[]>;
  /** The table sort, bound with `v-model:sort` and remembered across visits. */
  modelSort: Ref<DataTableSortColumn<BankConnection>>;
  /** Highlights the row of a connection, such as one just added. */
  highlight: (connection: BankConnectionIdentity) => void;
  rowClass: (row: BankConnection) => string;
  /** Whether a connection is syncing, from the backend or from a sync started here. */
  isSyncing: (row: BankConnection) => boolean;
  /** Runs `sync` with the connection marked as syncing until it settles. */
  whileSyncing: (connection: BankConnectionIdentity, sync: () => Promise<unknown>) => Promise<void>;
  /**
   * What a connection holds, ignored assets left out, the same total the bank balances page shows.
   * A connection that has not reported a balance yet holds zero.
   */
  balanceOf: (connection: BankConnectionIdentity) => BigNumber;
  /** Removes a connection the user already confirmed. */
  removeRow: (row: BankConnection) => Promise<void>;
  /** Why the last removal failed, named above the table until the next one starts. */
  removeFailure: Readonly<Ref<NamedFailure | undefined>>;
}

/**
 * The table on the Accounts banks page: its columns, sort, row highlight, each connection's balance
 * and removing a row.
 *
 * @param removeBank - removes a connection, throwing when the backend refuses
 */
export function useBankConnectionsTable(
  removeBank: (row: BankConnection) => Promise<boolean>,
): UseBankConnectionsTableReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { bankBalances } = storeToRefs(useBalancesStore());
  const { isAssetIgnored } = useAssetsStore();

  const modelSort = ref<DataTableSortColumn<BankConnection>>({
    column: 'name',
    direction: 'asc',
  });

  const cols = computed<DataTableColumn<BankConnection>[]>(() => [{
    cellClass: 'w-48',
    key: 'connector',
    label: t('bank_settings.form.bank'),
    sortable: true,
  }, {
    key: 'name',
    label: t('common.name'),
    sortable: true,
  }, {
    cellClass: 'h-15',
    key: 'syncStatus',
    label: t('bank_settings.header.last_sync'),
  }, {
    align: 'end',
    key: 'balance',
    label: t('common.value'),
  }, {
    align: 'center',
    cellClass: 'w-40',
    key: 'actions',
    label: t('common.actions_text'),
  }]);

  useRememberTableSorting<BankConnection>(TableId.BANKS, modelSort, cols);

  const { highlight, rowClass } = useRowHighlight<BankConnectionIdentity>(connectionKey);

  const totals = computed<Map<string, BigNumber>>(() => new Map(get(bankBalances).map(entry => [
    connectionKey(entry),
    exchangeAssetSum(entry.balances, isAssetIgnored),
  ])));

  const balanceOf = (connection: BankConnectionIdentity): BigNumber => get(totals).get(connectionKey(connection)) ?? Zero;

  const syncing = ref<string[]>([]);

  const isSyncing = (row: BankConnection): boolean => get(syncing).includes(connectionKey(row)) || row.syncStatus.running;

  async function whileSyncing(connection: BankConnectionIdentity, sync: () => Promise<unknown>): Promise<void> {
    const key = connectionKey(connection);
    set(syncing, [...get(syncing), key]);
    try {
      await sync();
    }
    finally {
      set(syncing, get(syncing).filter(item => item !== key));
    }
  }

  const { deleteRow: removeRow, failure: removeFailure } = useTableRowDeletion<BankConnection>({
    deleteItem: removeBank,
    failureTitle: () => t('bank_settings.errors.remove_title'),
  });

  return {
    balanceOf,
    cols,
    highlight,
    isSyncing,
    modelSort,
    removeFailure,
    removeRow,
    rowClass,
    whileSyncing,
  };
}

import type { BigNumber } from '@rotki/common';
import type { DataTableColumn, DataTableSortData } from '@rotki/ui-library';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { get, set } from '@vueuse/shared';
import { isEmpty } from 'es-toolkit/compat';
import { computed, type ComputedRef, type MaybeRefOrGetter, type Ref, shallowRef, toValue, type WritableComputedRef } from 'vue';
import { getAccountId, getGroupId } from '@/modules/accounts/account-utils';
import { sum } from '@/modules/core/common/display/balances';
import { type TableEmptyState, useTableEmptyState, useTableFetchError } from '@/modules/core/table/use-table-empty-state';
import { useAccountTableConfig } from './use-account-table-config';

interface UseAccountTableDataOptions<T extends BlockchainAccountBalance> {
  /** The page of accounts the table shows. */
  accounts: MaybeRefOrGetter<Collection<T>>;
  /** Chains switched off per group, which the row's chains leave out. */
  chainFilter: MaybeRefOrGetter<Record<string, string[]>>;
  /** The ids of the rows expanded in place, written as rows expand and collapse. */
  expandedIds: Ref<string[]>;
  /** The kind of account group the table lists, which picks the columns. */
  group: MaybeRefOrGetter<'evm' | 'xpub' | undefined>;
  /** The table has an `empty` slot to show in place of the generic empty text. */
  hasEmptySlot: MaybeRefOrGetter<boolean>;
  /** The table sorting, restored from and remembered under the account balances table. */
  sort: Ref<DataTableSortData<T>>;
}

interface UseAccountTableDataReturn<T extends BlockchainAccountBalance> {
  anyExpansion: ComputedRef<boolean>;
  cols: ComputedRef<DataTableColumn<AccountDataRow<T>>[]>;
  collapsed: Ref<AccountDataRow<T>[], AccountDataRow<T>[]>;
  expand: (item: AccountDataRow<T>) => void;
  emptyState: ComputedRef<TableEmptyState>;
  expanded: WritableComputedRef<AccountDataRow<T>[], AccountDataRow<T>[]>;
  getCategoryTotal: (category: string) => BigNumber;
  getChains: (row: AccountDataRow<T>) => string[];
  headerCategory: (group: Partial<AccountDataRow<T>>) => string;
  isExpanded: (row: AccountDataRow<T>) => boolean;
  rows: ComputedRef<AccountDataRow<T>[]>;
  showEmptySlot: ComputedRef<boolean>;
  totalValue: ComputedRef<BigNumber | undefined>;
}

export function useAccountTableData<T extends BlockchainAccountBalance>(
  options: UseAccountTableDataOptions<T>,
): UseAccountTableDataReturn<T> {
  const { accounts, chainFilter, expandedIds, group, hasEmptySlot, sort } = options;

  const emptyState = useTableEmptyState();
  const fetchError = useTableFetchError();
  /** A failed fetch is not something adding an account or clearing filters would fix. */
  const showEmptySlot = computed<boolean>(() => toValue(hasEmptySlot) && !(fetchError && get(fetchError)));

  const { createColumns, initializeTableSorting } = useAccountTableConfig<T>();

  const modelCollapsed = shallowRef<AccountDataRow<T>[]>([]);

  const rows = computed<AccountDataRow<T>[]>(() => {
    const data = toValue(accounts).data;
    return data.map(account => ({
      ...account,
      id: 'chain' in account ? getAccountId(account) : getGroupId(account),
    }));
  });

  const anyExpansion = computed<boolean>(() => get(rows).some(item => item.expansion));

  const expanded = computed<AccountDataRow<T>[]>({
    get() {
      return get(rows).filter(row => get(expandedIds).includes(row.id) && row.expansion);
    },
    set(value: AccountDataRow<T>[]) {
      set(expandedIds, value.map(row => row.id));
    },
  });

  const totalValue = computed<BigNumber | undefined>(() => {
    const totalVal = toValue(accounts).totalValue;
    if (!totalVal)
      return undefined;

    return totalVal.minus(sum(get(modelCollapsed)));
  });

  const cols = computed<DataTableColumn<AccountDataRow<T>>[]>(() => createColumns(toValue(group), get(anyExpansion)));

  initializeTableSorting(sort, cols);

  function getCategoryTotal(category: string): BigNumber {
    return sum(get(rows).filter(row => row.type === 'group' && row.category === category));
  }

  function getChains(row: AccountDataRow<T>): string[] {
    if (row.type === 'account')
      return [row.chain];

    const groupId = getGroupId(row);
    const excluded = toValue(chainFilter)[groupId] ?? [];

    return isEmpty(excluded)
      ? row.chains
      : row.chains.filter(chain => !excluded.includes(chain));
  }

  /** The category a table group header stands for; only group rows carry one. */
  function headerCategory(header: Partial<AccountDataRow<T>>): string {
    return 'category' in header && typeof header.category === 'string' ? header.category : '';
  }

  function getId(row: AccountDataRow<T>): string {
    return row.type === 'group' ? getGroupId(row) : getAccountId(row);
  }

  function isExpanded(row: AccountDataRow<T>): boolean {
    const rowId = getId(row);
    return get(expanded).some(item => item.id === rowId);
  }

  function expand(item: AccountDataRow<T>): void {
    set(expanded, isExpanded(item) ? [] : [item]);
  }

  return {
    anyExpansion,
    collapsed: modelCollapsed,
    cols,
    emptyState,
    expand,
    expanded,
    getCategoryTotal,
    getChains,
    headerCategory,
    isExpanded,
    rows,
    showEmptySlot,
    totalValue,
  };
}

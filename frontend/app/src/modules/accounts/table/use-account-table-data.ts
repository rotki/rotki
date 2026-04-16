import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter, Ref, WritableComputedRef } from 'vue';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import type { Collection } from '@/modules/core/common/collection';
import { isEmpty } from 'es-toolkit/compat';
import { getAccountId, getGroupId } from '@/modules/accounts/account-utils';
import { LOOPRING_CHAIN } from '@/modules/balances/blockchain-types';
import { sum } from '@/modules/core/common/display/balances';

interface UseAccountTableDataReturn<T extends BlockchainAccountBalance> {
  anyExpansion: ComputedRef<boolean>;
  collapsed: Ref<AccountDataRow<T>[], AccountDataRow<T>[]>;
  expand: (item: AccountDataRow<T>) => void;
  expanded: WritableComputedRef<AccountDataRow<T>[], AccountDataRow<T>[]>;
  getCategoryTotal: (category: string) => BigNumber;
  getChains: (row: AccountDataRow<T>) => string[];
  isExpanded: (row: AccountDataRow<T>) => boolean;
  isOnlyShowingLoopringChain: (row: AccountDataRow<T>) => boolean;
  isVirtual: (row: AccountDataRow<T>) => boolean;
  rows: ComputedRef<AccountDataRow<T>[]>;
  totalValue: ComputedRef<BigNumber | undefined>;
}

export function useAccountTableData<T extends BlockchainAccountBalance>(
  accounts: MaybeRefOrGetter<Collection<T>>,
  expandedIds: Ref<string[]>,
  chainFilter: Ref<Record<string, string[]>>,
): UseAccountTableDataReturn<T> {
  const collapsed = ref<AccountDataRow<T>[]>([]) as Ref<AccountDataRow<T>[]>;

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

    return totalVal.minus(sum(get(collapsed)));
  });

  function getCategoryTotal(category: string): BigNumber {
    return sum(get(rows).filter(row => row.category === category));
  }

  function getChains(row: AccountDataRow<T>): string[] {
    if (row.type === 'account')
      return [row.chain];

    const groupId = getGroupId(row);
    const excluded = get(chainFilter)[groupId] ?? [];

    return isEmpty(excluded)
      ? row.chains
      : row.chains.filter(chain => !excluded.includes(chain));
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

  function isVirtual(row: AccountDataRow<T>): boolean {
    return !!(('virtual' in row) && row.virtual);
  }

  function isOnlyShowingLoopringChain(row: AccountDataRow<T>): boolean {
    return ('chains' in row) && (row.chains.length === 1 && row.chains[0] === LOOPRING_CHAIN);
  }

  return {
    anyExpansion,
    collapsed,
    expand,
    expanded,
    getCategoryTotal,
    getChains,
    isExpanded,
    isOnlyShowingLoopringChain,
    isVirtual,
    rows,
    totalValue,
  };
}

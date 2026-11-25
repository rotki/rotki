import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { accountAddActivity, accountRemoveActivity } from '@/modules/accounts/accounts.activity';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalanceStatus, useChainLoadStates } from '@/modules/balances/use-balance-status';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseAccountLoadingStates<T extends BlockchainAccountBalance> {
  accountOperation: ComputedRef<boolean>;
  isInitialLoading: ComputedRef<boolean>;
  isRowLoading: (row: AccountDataRow<T>) => boolean;
  isSectionLoading: ComputedRef<boolean>;
}

export function useAccountLoadingStates<T extends BlockchainAccountBalance>(
  category: MaybeRefOrGetter<string>,
): UseAccountLoadingStates<T> {
  const { useIsActivePrefix } = useTaskCenter();
  const { refreshingChains } = storeToRefs(useBalanceRefreshState());
  const { isSectionLoading } = useBlockchainAccountLoading(category);
  const { chainIds } = useAccountCategoryHelper(category);
  const { loading: loadingChains } = useChainLoadStates(chainIds);
  const { isInitialLoading: anyInitialLoading } = useBalanceStatus();

  const accountOperation = logicOr(
    useIsActivePrefix(accountAddActivity.kind, ...accountAddActivity.partsWithin([])),
    useIsActivePrefix(accountRemoveActivity.kind, ...accountRemoveActivity.partsWithin([])),
    isSectionLoading,
  );

  /**
   * Whether the table has nothing to show *yet*, as opposed to nothing to show.
   *
   * @remarks
   * "Active" spans both layers: hydration is not an activity, so the orchestrator alone reports a
   * chain being read from the DB as idle. A category whose chain list has not resolved falls back
   * to every chain.
   */
  const isInitialLoading = computed<boolean>(() =>
    get(chainIds).length > 0 ? get(loadingChains).length > 0 : get(anyInitialLoading));

  function isRowLoading(row: AccountDataRow<T>): boolean {
    const refreshing = get(refreshingChains);
    if (row.type === 'account')
      return refreshing.has(row.chain);
    else
      return row.chains.some(chain => refreshing.has(chain));
  }

  return {
    accountOperation,
    isInitialLoading,
    isRowLoading,
    isSectionLoading,
  };
}

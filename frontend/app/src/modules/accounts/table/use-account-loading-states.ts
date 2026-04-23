import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AccountDataRow } from './types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { useAccountCategoryHelper } from '@/modules/accounts/use-account-category-helper';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-blockchain-account-loading';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { isCacheInitialLoading } from '@/modules/balances/use-balance-status';
import { Section } from '@/modules/core/common/status';
import { useStatusStore } from '@/modules/core/common/use-status-store';
import { TaskType } from '@/modules/core/tasks/task-type';
import { useTaskStore } from '@/modules/core/tasks/use-task-store';

interface UseAccountLoadingStates<T extends BlockchainAccountBalance> {
  accountOperation: ComputedRef<boolean>;
  isInitialLoading: ComputedRef<boolean>;
  isRowLoading: (row: AccountDataRow<T>) => boolean;
  isSectionLoading: ComputedRef<boolean>;
}

export function useAccountLoadingStates<T extends BlockchainAccountBalance>(
  category: MaybeRefOrGetter<string>,
): UseAccountLoadingStates<T> {
  const { useIsTaskRunning } = useTaskStore();
  const statusStore = useStatusStore();
  const { status } = storeToRefs(statusStore);
  const { refreshingChains } = storeToRefs(useBalanceRefreshState());
  const { isSectionLoading } = useBlockchainAccountLoading(category);
  const { chainIds } = useAccountCategoryHelper(category);

  const accountOperation = logicOr(
    useIsTaskRunning(TaskType.ADD_ACCOUNT),
    useIsTaskRunning(TaskType.REMOVE_ACCOUNT),
    isSectionLoading,
  );

  const isInitialLoading = computed<boolean>(() => {
    const chains = get(status)[Section.BLOCKCHAIN];
    if (!chains)
      return false;
    const categoryChains = get(chainIds);
    const candidates = categoryChains.length > 0
      ? categoryChains.filter(chain => chain in chains)
      : Object.keys(chains);
    if (candidates.length === 0)
      return false;
    return candidates.some(chain => isCacheInitialLoading(chains[chain]));
  });

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

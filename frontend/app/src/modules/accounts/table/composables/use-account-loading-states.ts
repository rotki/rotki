import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { AccountDataRow } from '../types';
import type { BlockchainAccountBalance } from '@/modules/accounts/blockchain-accounts';
import { useBlockchainAccountLoading } from '@/modules/accounts/use-account-loading';
import { Section } from '@/modules/common/status';
import { useStatusStore } from '@/modules/common/use-status-store';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

interface UseAccountLoadingStates<T extends BlockchainAccountBalance> {
  accountOperation: ComputedRef<boolean>;
  isAnyLoading: ComputedRef<boolean>;
  isRowLoading: (row: AccountDataRow<T>) => boolean;
  isSectionLoading: ComputedRef<boolean>;
}

export function useAccountLoadingStates<T extends BlockchainAccountBalance>(
  category: MaybeRefOrGetter<string>,
): UseAccountLoadingStates<T> {
  const { useIsTaskRunning } = useTaskStore();
  const { getIsLoading } = useStatusStore();
  const { isSectionLoading } = useBlockchainAccountLoading(category);

  const accountOperation = logicOr(
    useIsTaskRunning(TaskType.ADD_ACCOUNT),
    useIsTaskRunning(TaskType.REMOVE_ACCOUNT),
    isSectionLoading,
  );

  const isAnyLoading = logicOr(accountOperation, isSectionLoading);

  function isRowLoading(row: AccountDataRow<T>): boolean {
    if (row.type === 'account')
      return getIsLoading(Section.BLOCKCHAIN, row.chain);
    else
      return row.chains.some(chain => getIsLoading(Section.BLOCKCHAIN, chain));
  }

  return {
    accountOperation,
    isAnyLoading,
    isRowLoading,
    isSectionLoading,
  };
}

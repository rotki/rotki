import type { ComputedRef, Ref } from 'vue';
import type { AccountDataRow } from '../types';
import type { BlockchainAccountBalance } from '@/types/blockchain/accounts';
import { useBlockchainAccountLoading } from '@/composables/accounts/blockchain/use-account-loading';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

interface UseAccountLoadingStates<T extends BlockchainAccountBalance> {
  accountOperation: ComputedRef<boolean>;
  isAnyLoading: ComputedRef<boolean>;
  isRowLoading: (row: AccountDataRow<T>) => boolean;
  isSectionLoading: ComputedRef<boolean>;
}

export function useAccountLoadingStates<T extends BlockchainAccountBalance>(
  category: Ref<string>,
): UseAccountLoadingStates<T> {
  const { useIsTaskRunning } = useTaskStore();
  const { isLoading } = useStatusStore();
  const { isSectionLoading } = useBlockchainAccountLoading(category);

  const accountOperation = logicOr(
    useIsTaskRunning(TaskType.ADD_ACCOUNT),
    useIsTaskRunning(TaskType.REMOVE_ACCOUNT),
    isSectionLoading,
  );

  const isAnyLoading = logicOr(accountOperation, isSectionLoading);

  function isRowLoading(row: AccountDataRow<T>): boolean {
    if (row.type === 'account')
      return get(isLoading(Section.BLOCKCHAIN, row.chain));
    else
      return row.chains.some(chain => get(isLoading(Section.BLOCKCHAIN, chain)));
  }

  return {
    accountOperation,
    isAnyLoading,
    isRowLoading,
    isSectionLoading,
  };
}

import type { ComputedRef } from 'vue';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import { Blockchain } from '@rotki/common';
import { useAccountDelete } from '@/composables/accounts/blockchain/use-account-delete';
import { useSectionStatus } from '@/composables/status';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { Section } from '@/modules/common/status';
import { TaskType } from '@/modules/tasks/task-type';
import { useTaskStore } from '@/modules/tasks/use-task-store';

interface UseEthValidatorOperationsReturn {
  accountOperation: ComputedRef<boolean>;
  confirmDelete: (item: EthereumValidator) => void;
  deleteSelected: (rows: EthereumValidator[], selected: number[]) => void;
  edit: (account: EthereumValidator) => StakingValidatorManage;
  loading: ComputedRef<boolean>;
  refresh: () => Promise<void>;
}

export function useEthValidatorOperations(): UseEthValidatorOperationsReturn {
  const { showConfirmation } = useAccountDelete();
  const { fetchEthStakingValidators } = useEthStaking();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { useIsTaskRunning } = useTaskStore();
  const { isLoading: loading } = useSectionStatus(Section.BLOCKCHAIN, Blockchain.ETH2);

  const accountOperation = logicOr(
    useIsTaskRunning(TaskType.ADD_ACCOUNT),
    useIsTaskRunning(TaskType.REMOVE_ACCOUNT),
    loading,
  );

  function edit(account: EthereumValidator): StakingValidatorManage {
    const { index, ownershipPercentage, publicKey } = account;
    return {
      chain: Blockchain.ETH2,
      data: {
        ownershipPercentage: ownershipPercentage ?? '100',
        publicKey,
        validatorIndex: index.toString(),
      },
      mode: 'edit',
      type: 'validator',
    };
  }

  async function refresh(): Promise<void> {
    await fetchEthStakingValidators({ ignoreCache: true });
    await refreshBlockchainBalances({
      blockchain: Blockchain.ETH2,
    });
  }

  function confirmDelete(item: EthereumValidator): void {
    showConfirmation({
      data: [item],
      type: 'validator',
    });
  }

  function deleteSelected(rows: EthereumValidator[], selected: number[]): void {
    const items = rows.filter(item => selected.includes(item.index));
    showConfirmation({
      data: items,
      type: 'validator',
    });
  }

  return {
    accountOperation,
    confirmDelete,
    deleteSelected,
    edit,
    loading,
    refresh,
  };
}

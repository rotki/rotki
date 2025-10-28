import type { ComputedRef } from 'vue';
import type { StakingValidatorManage } from '@/composables/accounts/blockchain/use-account-manage';
import type { EthereumValidator } from '@/types/blockchain/accounts';
import { Blockchain } from '@rotki/common';
import { useAccountDelete } from '@/composables/accounts/blockchain/use-account-delete';
import { useEthStaking } from '@/composables/blockchain/accounts/staking';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { useStatusStore } from '@/store/status';
import { useTaskStore } from '@/store/tasks';
import { Section } from '@/types/status';
import { TaskType } from '@/types/task-type';

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
  const { fetchBlockchainBalances } = useBlockchainBalances();
  const { useIsTaskRunning } = useTaskStore();
  const { isLoading } = useStatusStore();

  const loading = isLoading(Section.BLOCKCHAIN, Blockchain.ETH2);

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
    await fetchBlockchainBalances({
      blockchain: Blockchain.ETH2,
      ignoreCache: true,
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

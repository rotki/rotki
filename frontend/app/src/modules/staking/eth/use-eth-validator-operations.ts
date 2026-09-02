import type { ComputedRef } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import { Blockchain } from '@rotki/common';
import { useAccountDelete } from '@/modules/accounts/blockchain/use-account-delete';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { ActivityKind, ActivityPart } from '@/modules/task-center/core/types';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

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
  const { useIsActivePrefix } = useTaskCenter();
  // Both layers: hydration is not an activity, so the orchestrator alone reports a DB read as idle.
  const loading = logicOr(
    useIsActivePrefix(ActivityKind.BLOCKCHAIN_BALANCES, Blockchain.ETH2),
    useBalanceRefreshState().useIsHydrating(Blockchain.ETH2),
  );

  const accountOperation = logicOr(
    useIsActivePrefix(ActivityKind.ACCOUNTS, ActivityPart.ADD),
    useIsActivePrefix(ActivityKind.ACCOUNTS, ActivityPart.REMOVE),
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

  /**
   * Re-reads the validator list and their eth2 balances, bypassing every cache.
   *
   * @remarks
   * Submitted at user priority, which supersedes an eth2 query already in flight instead of
   * queueing behind it. That is what a refresh button owes the user: they said the numbers on
   * screen are stale, and joining a background pass would hand back the same ones.
   */
  async function refresh(): Promise<void> {
    await fetchEthStakingValidators({ ignoreCache: true });
    await refreshBlockchainBalances({
      blockchain: Blockchain.ETH2,
    }, RefreshMode.USER);
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

import type { ComputedRef, Ref } from 'vue';
import type { EthereumValidator } from '@/modules/accounts/blockchain-accounts';
import type { StakingValidatorManage } from '@/modules/accounts/blockchain/use-account-manage';
import type { ConfirmQuestion } from '@/modules/shell/components/confirm-question';
import { Blockchain } from '@rotki/common';
import { accountAddActivity, accountRemoveActivity } from '@/modules/accounts/accounts.activity';
import { useAccountDelete } from '@/modules/accounts/blockchain/use-account-delete';
import { useEthStaking } from '@/modules/accounts/use-eth-staking';
import { chainBalancesActivity } from '@/modules/balances/balances.activity';
import { RefreshMode } from '@/modules/balances/types/refresh-mode';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBlockchainBalances } from '@/modules/balances/use-blockchain-balances';
import { type NamedFailure, useFailureSlot } from '@/modules/shell/components/named-failure';
import { useDeleteQuestion } from '@/modules/shell/components/row-delete-question';
import { useTaskCenter } from '@/modules/task-center/use-task-center';

interface UseEthValidatorOperationsReturn {
  accountOperation: ComputedRef<boolean>;
  /** What a row's delete button asks, beside it, before `deleteValidator` runs. */
  deleteConfirm: (item: EthereumValidator) => ConfirmQuestion;
  /** Deletes a validator the user already confirmed. */
  deleteValidator: (item: EthereumValidator) => Promise<void>;
  /**
   * What the toolbar's delete asks, beside it, before `deleteSelected` runs.
   *
   * @returns Nothing while no validator in `rows` is selected, since there is nothing to describe.
   */
  deleteSelectedConfirm: (rows: EthereumValidator[], selected: number[]) => ConfirmQuestion | undefined;
  /** Deletes the selected validators out of `rows`, which the toolbar already confirmed. */
  deleteSelected: (rows: EthereumValidator[], selected: number[]) => Promise<void>;
  /** Why the last single or bulk delete failed, named above the table. */
  deleteFailure: Readonly<Ref<NamedFailure | undefined>>;
  edit: (account: EthereumValidator) => StakingValidatorManage;
  loading: ComputedRef<boolean>;
  refresh: () => Promise<void>;
}

export function useEthValidatorOperations(): UseEthValidatorOperationsReturn {
  const { deleteConfirmed, describeDeletion } = useAccountDelete();
  const { failure: deleteFailure, run } = useFailureSlot();
  const deleteQuestion = useDeleteQuestion();
  const { t } = useI18n({ useScope: 'global' });
  const { fetchEthStakingValidators } = useEthStaking();
  const { refreshBlockchainBalances } = useBlockchainBalances();
  const { useIsActivePrefix } = useTaskCenter();
  // Both layers: hydration is not an activity, so the orchestrator alone reports a DB read as idle.
  const loading = logicOr(
    useIsActivePrefix(chainBalancesActivity.kind, ...chainBalancesActivity.partsWithin([Blockchain.ETH2])),
    useBalanceRefreshState().useIsHydrating(Blockchain.ETH2),
  );

  const accountOperation = logicOr(
    useIsActivePrefix(accountAddActivity.kind, ...accountAddActivity.partsWithin([])),
    useIsActivePrefix(accountRemoveActivity.kind, ...accountRemoveActivity.partsWithin([])),
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

  function describe(data: EthereumValidator[]): ConfirmQuestion {
    return deleteQuestion({
      message: describeDeletion({ data, type: 'validator' }),
      title: t('account_balances.confirm_delete.title'),
    });
  }

  function deleteConfirm(item: EthereumValidator): ConfirmQuestion {
    return describe([item]);
  }

  function pick(rows: EthereumValidator[], selected: number[]): EthereumValidator[] {
    return rows.filter(item => selected.includes(item.index));
  }

  function deleteSelectedConfirm(rows: EthereumValidator[], selected: number[]): ConfirmQuestion | undefined {
    const picked = pick(rows, selected);
    return picked.length > 0 ? describe(picked) : undefined;
  }

  async function deleteValidators(data: EthereumValidator[]): Promise<void> {
    await run(
      t('actions.delete_eth2_validator.error.title'),
      async () => deleteConfirmed({ data, type: 'validator' }),
    );
  }

  async function deleteValidator(item: EthereumValidator): Promise<void> {
    await deleteValidators([item]);
  }

  async function deleteSelected(rows: EthereumValidator[], selected: number[]): Promise<void> {
    const picked = pick(rows, selected);
    if (picked.length > 0)
      await deleteValidators(picked);
  }

  return {
    accountOperation,
    deleteConfirm,
    deleteFailure,
    deleteSelected,
    deleteSelectedConfirm,
    deleteValidator,
    edit,
    loading,
    refresh,
  };
}

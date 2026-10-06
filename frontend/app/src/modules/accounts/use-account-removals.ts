import type { DeleteBlockchainAccountParams, DeleteXpubParams } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { accountActivityLabel, accountAgnosticRemoveActivity, accountRemoveActivity, type AccountSubject } from '@/modules/accounts/accounts.activity';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { logger } from '@/modules/core/common/logging/logging';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAccountRemovalsReturn {
  removeAccount: (payload: DeleteBlockchainAccountParams) => Promise<Result<void, TaskError>>;
  removeAgnosticAccount: (chainType: string, address: string) => Promise<Result<void, TaskError>>;
  deleteXpub: (params: DeleteXpubParams) => Promise<Result<void, TaskError>>;
}

export function useAccountRemovals(): UseAccountRemovalsReturn {
  const {
    deleteXpub: deleteXpubCaller,
    removeAgnosticBlockchainAccount,
    removeBlockchainAccount,
  } = useBlockchainAccountsApi();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  /** A failed removal is the activity's dock row; a cancellation is not logged. */
  const logRemovalFailure = (outcome: Result<unknown, TaskError>): void => {
    if (isErr(outcome) && isActionable(outcome.error))
      logger.error(outcome.error.message);
  };

  const removeAccount = async (payload: DeleteBlockchainAccountParams): Promise<Result<void, TaskError>> => {
    const { accounts, chain } = payload;
    const subject: AccountSubject = { chain, target: { addresses: accounts, kind: 'addresses' } };
    const outcome = await submitTask({
      id: accountRemoveActivity.id(subject),
      kind: accountRemoveActivity.kind,
      lane: accountRemoveActivity.laneOf?.(subject),
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BlockchainBalances>(
          async () => removeBlockchainAccount(chain, accounts),
        ),
        () => {},
      ),
      subtitle: accountActivityLabel.removeCount(accounts.length),
      title: t('task_center.group.accounts'),
    });

    logRemovalFailure(outcome);

    return outcome;
  };

  const removeAgnosticAccount = async (chainType: string, address: string): Promise<Result<void, TaskError>> => {
    const subject = { address, category: chainType };
    const outcome = await submitTask({
      id: accountAgnosticRemoveActivity.id(subject),
      kind: accountAgnosticRemoveActivity.kind,
      lane: accountAgnosticRemoveActivity.laneOf?.(subject),
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<BlockchainBalances>(
          async () => removeAgnosticBlockchainAccount(chainType, [address]),
        ),
        () => {},
      ),
      subtitle: accountActivityLabel.remove(address),
      title: t('task_center.group.accounts'),
    });

    logRemovalFailure(outcome);

    return outcome;
  };

  const deleteXpub = async (params: DeleteXpubParams): Promise<Result<void, TaskError>> => {
    const subject: AccountSubject = {
      chain: params.chain,
      target: { derivationPath: params.derivationPath, kind: 'xpub', xpub: params.xpub },
    };
    const outcome = await submitTask({
      id: accountRemoveActivity.id(subject),
      kind: accountRemoveActivity.kind,
      lane: accountRemoveActivity.laneOf?.(subject),
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => deleteXpubCaller(params),
        ),
        () => {},
      ),
      subtitle: accountActivityLabel.removeXpub(params.xpub),
      title: t('task_center.group.accounts'),
    });

    logRemovalFailure(outcome);
    return outcome;
  };

  return { deleteXpub, removeAccount, removeAgnosticAccount };
}

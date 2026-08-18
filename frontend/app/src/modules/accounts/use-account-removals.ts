import type { DeleteBlockchainAccountParams, DeleteXpubParams } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { accountActivityLabel, accountAgnosticRemoveActivity, accountRemoveActivity, type AccountSubject } from '@/modules/accounts/accounts.activity';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
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
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * Removals report a real failure and stay silent on a cancellation, which is what `isActionable`
   * distinguishes. All three removals notify the same way, differing only in their title.
   */
  const notifyRemovalFailure = (outcome: Result<unknown, TaskError>, title: string): void => {
    if (!isErr(outcome) || !isActionable(outcome.error))
      return;

    logger.error(outcome.error.message);
    notifyError(title, t('actions.balances.blockchain_account_removal.error.description', {
      error: outcome.error.message,
    }));
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

    notifyRemovalFailure(outcome, t('actions.balances.blockchain_account_removal.error.title', {
      blockchain: chain,
      count: accounts.length,
    }));

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

    notifyRemovalFailure(outcome, t('actions.balances.blockchain_account_removal.agnostic.error.title', { address }));

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

    // The xpub removal keeps its own message: it names the xpub, not a chain or a count.
    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      notifyError(t('actions.balances.xpub_removal.error.title'), t('actions.balances.xpub_removal.error.description', {
        error: outcome.error.message,
        xpub: params.xpub,
      }));
    }

    return outcome;
  };

  return { deleteXpub, removeAccount, removeAgnosticAccount };
}

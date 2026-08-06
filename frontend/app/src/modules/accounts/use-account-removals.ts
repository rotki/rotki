import type { DeleteBlockchainAccountParams, DeleteXpubParams } from '@/modules/accounts/blockchain-accounts';
import type { BlockchainBalances } from '@/modules/balances/types/blockchain-balances';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { accountActivityLabel, accountRemoveActivity, type AccountSubject } from '@/modules/accounts/accounts.activity';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAccountRemovalsReturn {
  removeAccount: (payload: DeleteBlockchainAccountParams) => Promise<void>;
  removeAgnosticAccount: (chainType: string, address: string) => Promise<void>;
  deleteXpub: (params: DeleteXpubParams) => Promise<void>;
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

  const removeAccount = async (payload: DeleteBlockchainAccountParams): Promise<void> => {
    const { accounts, chain } = payload;
    const subject: AccountSubject = { chain, target: { addresses: accounts, kind: 'addresses' } };
    const outcome = await submitTask({
      id: accountRemoveActivity.id(subject),
      kind: accountRemoveActivity.kind,
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
  };

  /**
   * ⚠️ Keyed by chain *type*, not chain, so it shares a keyspace with {@link removeAccount} without
   * sharing its subject — which is why it has no descriptor. Two agnostic removals of different
   * addresses under one chain type still collide, the same hazard the descriptors fixed elsewhere;
   * left as-is here so this move stays a pure move.
   */
  const removeAgnosticAccount = async (chainType: string, address: string): Promise<void> => {
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.REMOVE, chainType),
      kind: ActivityKind.ACCOUNTS,
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
  };

  const deleteXpub = async (params: DeleteXpubParams): Promise<void> => {
    const subject: AccountSubject = {
      chain: params.chain,
      target: { derivationPath: params.derivationPath, kind: 'xpub', xpub: params.xpub },
    };
    const outcome = await submitTask({
      id: accountRemoveActivity.id(subject),
      kind: accountRemoveActivity.kind,
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
  };

  return { deleteXpub, removeAccount, removeAgnosticAccount };
}

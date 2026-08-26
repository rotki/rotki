import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { EvmAccountsResult } from '@/modules/core/api/types/accounts';
import type { ActivityId } from '@/modules/task-center/core/types';
import { err, flatMap as flatMapResult, map as mapResult, ok, type Result } from 'plainfp/result';
import { accountActivityLabel, accountAddActivity, type AccountSubject, accountTargetOf, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/**
 * `parent` is passed explicitly rather than picked up from ambient state. A module-scoped "current
 * batch" would read more cleanly at the call sites, but it only works while every submit happens in
 * the synchronous prologue of the batch callback — an `await` introduced anywhere above it would
 * silently orphan the child from its umbrella, with nothing to report it.
 */
export interface AdditionOptions {
  readonly parent?: ActivityId;
}

interface UseAccountAdditionsReturn {
  /**
   * The added address on success. Failure stays a value: `TaskError` distinguishes a cancelled
   * add from a failed one, which a bare string could not.
   */
  addAccount: (chain: string, payload: AccountPayload[] | XpubAccountPayload, options?: AdditionOptions) => Promise<Result<string, TaskError>>;
  addEvmAccount: (payload: AccountPayload, options?: AdditionOptions) => Promise<Result<EvmAccountsResult, TaskError>>;
}

export function useAccountAdditions(): UseAccountAdditionsReturn {
  const { addBlockchainAccount, addEvmAccount: addEvmAccountCaller } = useBlockchainAccountsApi();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  /**
   * Adds one account, or one xpub, and reports the address the backend actually stored.
   *
   * @remarks
   * A cancellation, a failure and an empty result are all the error branch. Nothing was added in
   * any of them, so there is no address to hand back, and an `ok('')` would put `{ address: '' }`
   * into `addedAccounts` and refresh on a blank address.
   */
  const addAccount = async (
    chain: string,
    payload: AccountPayload[] | XpubAccountPayload,
    options?: AdditionOptions,
  ): Promise<Result<string, TaskError>> => {
    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub.xpub;
    const subject = { chain, target: accountTargetOf(payload) };
    const outcome = await submitTask<string[] | true>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
      parent: options?.parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<string[] | true, TaskError>> => mapResult(
        await runTask<string[] | true>(
          async () => addBlockchainAccount(chain, payload),
        ),
        value => value,
      ),
      subtitle: accountActivityLabel.add(address),
      title: t('task_center.group.accounts'),
    });

    return flatMapResult(outcome, (result) => {
      if (result === true)
        return ok(address);

      // Translated, because this message is user-facing: `errorOf` hands it back and the account
      // form renders `error.message` in its dialog.
      return result.length > 0
        ? ok(result[0])
        : err(TaskFailed({ message: t('actions.balances.blockchain_accounts_add.error.nothing_added', { address }) }));
    });
  };

  const addEvmAccount = async (
    { address, label, tags }: AccountPayload,
    options?: AdditionOptions,
  ): Promise<Result<EvmAccountsResult, TaskError>> => {
    // The pseudo-chain, not a real one: this asks for every EVM chain at once.
    const subject: AccountSubject = { chain: EVM_PSEUDO_CHAIN, target: { address, kind: 'address' } };
    const outcome = await submitTask<EvmAccountsResult>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
      parent: options?.parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<EvmAccountsResult, TaskError>> => mapResult(
        await runTask<EvmAccountsResult>(
          async () => addEvmAccountCaller({ address, label, tags }),
        ),
        value => value,
      ),
      subtitle: accountActivityLabel.add(address),
      title: t('task_center.group.accounts'),
    });

    // As in `addAccount`: `{}` conflated a cancelled/failed add with an empty result.
    return outcome;
  };

  return { addAccount, addEvmAccount };
}

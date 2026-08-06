import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { EvmAccountsResult } from '@/modules/core/api/types/accounts';
import { err, flatMap as flatMapResult, map as mapResult, ok, type Result } from 'plainfp/result';
import { accountActivityLabel, accountAddActivity, type AccountSubject, accountTargetOf, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface UseAccountAdditionsReturn {
  /**
   * The added address on success. Failure stays a value: `TaskError` distinguishes a cancelled
   * add from a failed one, which a bare string could not.
   */
  addAccount: (chain: string, payload: AccountPayload[] | XpubAccountPayload) => Promise<Result<string, TaskError>>;
  addEvmAccount: (payload: AccountPayload) => Promise<Result<EvmAccountsResult, TaskError>>;
}

export function useAccountAdditions(): UseAccountAdditionsReturn {
  const { addBlockchainAccount, addEvmAccount: addEvmAccountCaller } = useBlockchainAccountsApi();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  const addAccount = async (chain: string, payload: AccountPayload[] | XpubAccountPayload): Promise<Result<string, TaskError>> => {
    const address = Array.isArray(payload) ? payload.map(item => item.address).join(',\n') : payload.xpub.xpub;
    const subject = { chain, target: accountTargetOf(payload) };
    const outcome = await submitTask<string[] | true>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
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

    // `''` used to mean three different things at once: cancelled, non-actionable failure, and a
    // genuinely empty result. The caller read all three as a successful addition, so a cancelled
    // add was reported as added. Cancellation and failure are now the error branch, and an empty
    // result joins them: nothing was added, so there is no address to hand back, and returning
    // `ok('')` would put `{ address: '' }` into `addedAccounts` and refresh on a blank address.
    return flatMapResult(outcome, (result) => {
      if (result === true)
        return ok(address);

      return result.length > 0
        ? ok(result[0])
        : err(TaskFailed({ message: `no account was added for ${address}` }));
    });
  };

  const addEvmAccount = async ({ address, label, tags }: AccountPayload): Promise<Result<EvmAccountsResult, TaskError>> => {
    // The pseudo-chain, not a real one: this asks for every EVM chain at once.
    const subject: AccountSubject = { chain: EVM_PSEUDO_CHAIN, target: { address, kind: 'address' } };
    const outcome = await submitTask<EvmAccountsResult>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
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

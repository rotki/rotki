import type { AccountPayload, XpubAccountPayload } from '@/modules/accounts/blockchain-accounts';
import type { EvmAccountsResult } from '@/modules/core/api/types/accounts';
import type { ActivityId } from '@/modules/task-center/core/types';
import { err, flatMap as flatMapResult, map as mapResult, ok, type Result } from 'plainfp/result';
import { type MessageKey, msg } from '@/message-key';
import { accountActivityLabel, accountAddActivity, type AccountSubject, type AccountTarget, accountTargetLabel, accountTargetOf, EVM_PSEUDO_CHAIN } from '@/modules/accounts/accounts.activity';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { evmAdditionOutcome, EvmSkipReason } from '@/modules/accounts/evm-addition-outcome';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { publishActivityDetail } from '@/modules/task-center/use-activity-detail';
import { useNativeTask } from '@/modules/task-center/use-native-task';

/** The reason a skipped "every EVM chain" addition shows on its row. */
const EVM_SKIP_MESSAGE: Record<EvmSkipReason, MessageKey> = {
  [EvmSkipReason.EXISTED]: msg.$t('actions.balances.blockchain_accounts_add.skipped.existed'),
  [EvmSkipReason.NO_ACTIVITY]: msg.$t('actions.balances.blockchain_accounts_add.skipped.no_activity'),
};

/**
 * `parent` is passed explicitly rather than picked up from ambient state. A module-scoped "current
 * batch" would read more cleanly at the call sites, but it only works while every submit happens in
 * the synchronous prologue of the batch callback — an `await` introduced anywhere above it would
 * silently orphan the child from its umbrella, with nothing to report it.
 */
export interface AdditionOptions {
  readonly parent?: ActivityId;
  /**
   * The user asked for this addition, so the dock opens to report it. Left to the caller: an
   * addition that reports inline beside its own control (the Gnosis Pay safe) must not also open
   * the dock over it.
   */
  readonly userStarted?: boolean;
}

interface UseAccountAdditionsReturn {
  /**
   * The added address on success. Failure stays a value: `TaskError` distinguishes a cancelled
   * add from a failed one, which a bare string could not.
   */
  addAccount: (chain: string, payload: AccountPayload[] | XpubAccountPayload, options?: AdditionOptions) => Promise<Result<string, TaskError>>;
  addEvmAccount: (payload: AccountPayload, options?: AdditionOptions) => Promise<Result<EvmAccountsResult, TaskError>>;
  reportTracked: (chain: string, target: AccountTarget, options?: AdditionOptions) => Promise<void>;
}

export function useAccountAdditions(): UseAccountAdditionsReturn {
  const { addBlockchainAccount, addEvmAccount: addEvmAccountCaller } = useBlockchainAccountsApi();
  const { submitTask } = useNativeTask();
  const { getChainName } = useSupportedChains();
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
    const target = accountTargetOf(payload);
    const address = accountTargetLabel(target);
    const subject = { chain, target };
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
      userStarted: options?.userStarted,
    });

    return flatMapResult(outcome, (result) => {
      if (result === true)
        return ok(address);

      return result.length > 0
        ? ok(result[0])
        : err(TaskFailed({ message: t('actions.balances.blockchain_accounts_add.error.nothing_added', { address }) }));
    });
  };

  /**
   * The activity's verdict on one address's answer: added, skipped with a reason, or failed.
   *
   * @remarks
   * Decided inside the run, not by the caller, because the verdict is the activity's status: an
   * address the backend tracked nowhere must not settle COMPLETE while the dock reports it as done.
   * The per-chain breakdown is published only for an address that was added, since a skipped or
   * failed row already says what happened in its reason.
   *
   * Only the "no activity" skip asks for attention: that address is now tracked nowhere, which the
   * user has to know, whereas one already tracked everywhere is exactly what they wanted.
   */
  const settleEvmAddition = (subject: AccountSubject, result: EvmAccountsResult): Result<EvmAccountsResult, TaskError> => {
    const outcome = evmAdditionOutcome(result);
    switch (outcome.type) {
      case 'added':
        publishActivityDetail(accountAddActivity, subject, outcome.detail);
        return ok(result);
      case 'skipped':
        return err(Skipped({ attention: outcome.reason === EvmSkipReason.NO_ACTIVITY, message: t(EVM_SKIP_MESSAGE[outcome.reason]) }));
      case 'failed':
        return err(TaskFailed({
          message: t('actions.balances.blockchain_accounts_add.error.failed_chains', {
            chains: outcome.chains.map(chain => getChainName(chain)).join(', '),
          }),
        }));
    }
  };

  const addEvmAccount = async (
    { address, label, tags }: AccountPayload,
    options?: AdditionOptions,
  ): Promise<Result<EvmAccountsResult, TaskError>> => {
    const subject: AccountSubject = { chain: EVM_PSEUDO_CHAIN, target: { address, kind: 'address' } };
    const outcome = await submitTask<EvmAccountsResult>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      lane: accountAddActivity.laneOf?.(subject),
      parent: options?.parent,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<EvmAccountsResult, TaskError>> => flatMapResult(
        await runTask<EvmAccountsResult>(
          async () => addEvmAccountCaller({ address, label, tags }),
        ),
        result => settleEvmAddition(subject, result),
      ),
      subtitle: accountActivityLabel.add(address),
      title: t('task_center.group.accounts'),
      userStarted: options?.userStarted,
    });

    return outcome;
  };

  /**
   * Reports an account the user asked to add that is already tracked, as a skipped addition. Sends
   * nothing to the backend: it exists so the dock accounts for every row of an import, not only the
   * rows that needed work.
   */
  const reportTracked = async (chain: string, target: AccountTarget, options?: AdditionOptions): Promise<void> => {
    const subject: AccountSubject = { chain, target };
    await submitTask<never>({
      id: accountAddActivity.id(subject),
      kind: accountAddActivity.kind,
      parent: options?.parent,
      rerunnable: false,
      run: async (): Promise<Result<never, TaskError>> => err(Skipped({ message: t('actions.balances.blockchain_accounts_add.skipped.tracked') })),
      subtitle: accountActivityLabel.add(accountTargetLabel(target)),
      title: t('task_center.group.accounts'),
      userStarted: options?.userStarted,
    });
  };

  return { addAccount, addEvmAccount, reportTracked };
}

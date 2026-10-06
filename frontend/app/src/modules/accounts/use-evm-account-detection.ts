import type { EvmChainLikeAddress } from '@/modules/history/events/event-payloads';
import { isErr, ok, type Result } from 'plainfp/result';
import { useBlockchainAccountsApi } from '@/modules/accounts/api/use-blockchain-accounts-api';
import { useAccountLoadState } from '@/modules/accounts/use-account-load-state';
import { useAccountOperations } from '@/modules/accounts/use-account-operations';
import { accountKey, useDetectedAccountsStore } from '@/modules/accounts/use-detected-accounts-store';
import { useAccountAddresses } from '@/modules/balances/blockchain/use-account-addresses';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { activityLabel } from '@/modules/task-center/activity-labels';
import { type ActivityContext, ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

interface UseEvmAccountDetectionReturn {
  detectEvmAccounts: () => Promise<void>;
}

/**
 * Runs EVM account detection from the Detect button and keeps what it found, for the marks in the
 * accounts table and the outcome the button reports.
 *
 * @remarks
 * The found accounts come from the tracked accounts before the run compared with a read after it,
 * not from the `evmlike_accounts_detection` websocket message. The backend sends that message while
 * the task result is polled, so nothing orders the two, and a message landing after the result
 * would report "nothing found" for a run that found something.
 */
export function useEvmAccountDetection(): UseEvmAccountDetectionReturn {
  const { detectEvmAccounts: detectEvmAccountsCaller } = useBlockchainAccountsApi();
  const { fetchAccounts } = useAccountOperations();
  const { pending } = useAccountLoadState();
  const { getAddresses } = useAccountAddresses();
  const { evmAndEvmLikeTxChainsInfo } = useSupportedChains();
  const { beginRun, record, setLastRun, wasAddedByUser } = useDetectedAccountsStore();
  const { submitTask } = useNativeTask();
  const { t } = useI18n({ useScope: 'global' });

  function trackedAccounts(chains: string[]): EvmChainLikeAddress[] {
    return chains.flatMap(chain => getAddresses(chain).map(address => ({ address, chain })));
  }

  /**
   * One detection run, from the snapshot to the recorded outcome.
   *
   * @remarks
   * All of it lives in the task's `run`, because a retry from the task dock re-runs only that: a
   * snapshot taken outside would leave a retried run marking nothing. The snapshot waits for the
   * account load, since a store still filling one chain at a time would count every account it
   * had not read yet as found.
   */
  const runDetection = async ({ cancelled, runTask }: ActivityContext): Promise<Result<void, TaskError>> => {
    setLastRun(undefined);
    await pending();
    if (cancelled())
      return ok(undefined);

    const chains = get(evmAndEvmLikeTxChainsInfo).map(chain => chain.id);
    const before = new Set(trackedAccounts(chains).map(accountKey));
    beginRun();

    const detection = await runTask<unknown>(async () => detectEvmAccountsCaller());
    if (isErr(detection))
      return detection;

    await fetchAccounts({ blockchain: chains });
    if (cancelled())
      return ok(undefined);

    const found = trackedAccounts(chains).filter(account => !before.has(accountKey(account)) && !wasAddedByUser(account));
    record(found);
    setLastRun(found);
    return ok(undefined);
  };

  const detectEvmAccounts = async (): Promise<void> => {
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ACCOUNTS, ActivityPart.DETECT),
      kind: ActivityKind.ACCOUNTS,
      rerunnable: true,
      run: runDetection,
      subtitle: activityLabel(ActivityKind.ACCOUNTS, ActivityPart.DETECT),
      title: t('task_center.group.accounts'),
    });

    if (isErr(outcome) && isActionable(outcome.error))
      logger.error(outcome.error.message);
  };

  return {
    detectEvmAccounts,
  };
}

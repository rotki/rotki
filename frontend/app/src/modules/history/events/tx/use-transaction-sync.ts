import { groupBy } from 'es-toolkit';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { msg } from '@/message-key';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { combineOutcomes, isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { type BlockchainAddress, type ChainAddress, type TransactionChainType, TransactionChainTypeNeedDecoding, type TransactionRequestPayload } from '@/modules/history/events/event-payloads';
import { accountSyncActivity, accountSyncActivityId, chainSyncActivity, chainSyncActivityId } from '@/modules/history/events/tx/sync-activity';
import { useHistoryTransactionAccounts } from '@/modules/history/events/tx/use-history-transaction-accounts';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { type ActivityId, ActivityStatus } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface TransactionSyncParams {
  accounts: ChainAddress[];
  type: TransactionChainType;
}

/** A chain activity's declared children, split by whether they decide the chain's own outcome. */
interface ChainSubtree {
  readonly accounts: readonly Promise<Result<void, TaskError>>[];
  readonly decode: readonly Promise<void>[];
}

/**
 * The per-chain and per-account syncs report their outcome rather than swallowing it: a parent
 * settles on what its children actually did, and the sync's own error handling (notifications)
 * still happens where the failure is, not at the caller.
 */
interface UseTransactionSyncReturn {
  syncAndReDecodeEvents: (chain: string, params: TransactionSyncParams, parent?: ActivityId) => Promise<Result<void, TaskError>>;
  syncTransactionTask: (account: ChainAddress, parent?: ActivityId) => Promise<Result<void, TaskError>>;
  syncTransactionsByChains: (accounts: ChainAddress[], parent?: ActivityId) => Promise<Result<void, TaskError>[]>;
}

export function useTransactionSync(): UseTransactionSyncReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { fetchTransactionsTask } = useHistoryEventsApi();

  const { statusOf, submitTask } = useNativeTask();
  const { getChainName } = useSupportedChains();
  const { decodeTransactionsTask } = useHistoryTransactionDecoding();
  const { getTransactionTypeFromChain } = useHistoryTransactionAccounts();

  /**
   * Whether an account's latest sync ended cancelled.
   *
   * Read from the orchestrator, which settles an activity before anything waiting on it can start,
   * so a decode checking this as it starts sees every account's outcome. A cancel from the backend
   * counts the same as one from the user: either way that account's query never finished.
   */
  const wasCancelled = (account: ChainAddress): boolean =>
    statusOf(accountSyncActivity.kind, ...accountSyncActivity.partsOf(account)).lastOutcome === ActivityStatus.CANCELLED;

  /**
   * Tells the user about a failed query they can act on.
   *
   * The failure itself needs no recording here: it is the account activity's own status, which the
   * dock reports. A skip or a cancellation is not something to act on, so neither is announced.
   */
  const notifyQueryFailure = (error: TaskError, account: ChainAddress, chainName: string): void => {
    if (!isActionable(error))
      return;

    notifyError(
      t('actions.transactions.error.title'),
      t('actions.transactions.error.description', {
        address: account.address,
        chain: chainName,
        error: error.message,
      }),
    );
  };

  /**
   * Syncs one account's transactions on one chain, as its own native activity.
   *
   * @remarks
   * One `TX_SYNC` activity per chain and address, on that chain's own lane, so the family cap gives
   * two concurrent accounts *per chain*. Liveness, cancellation and re-run are the orchestrator's;
   * the chain grouping and the decode hand-off belong to {@link syncAndReDecodeEvents}. The query's
   * progress arrives separately, from the backend's frames; see `createTransactionStatusHandler`.
   */
  const syncTransactionTask = async (
    account: ChainAddress,
    parent?: ActivityId,
  ): Promise<Result<void, TaskError>> => {
    const { address, chain } = account;

    const blockchainAccount: BlockchainAddress = {
      address,
      blockchain: chain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    const chainName = getChainName(chain);
    const outcome = await submitTask({
      id: accountSyncActivity.id(account),
      kind: accountSyncActivity.kind,
      lane: accountSyncActivity.laneOf?.(account),
      parent,
      rerunnable: true,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => fetchTransactionsTask(defaults),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(msg.$t('task_center.activity.tx_sync.address'), { address, chain: chainName }),
      title: t('task_center.group.tx_sync'),
    });

    if (isErr(outcome)) {
      if (hasTag(outcome.error, 'BackendCancelled'))
        logger.debug(outcome.error.message);
      else
        notifyQueryFailure(outcome.error, account, chainName);
    }

    return outcome;
  };

  /**
   * One chain's sync, as its own activity, with its whole subtree declared in the same tick: the
   * per-account syncs and the decode that follows them all exist before any of it runs, so the
   * task center shows the shape of a refresh rather than discovering it.
   *
   * Concurrency stays the scheduler's and stays nested: the chain on {@link CHAIN_SYNC_LANE} (2 at a
   * time), its accounts on the chain's own lane (2 each, 2 chains' lanes live at once), the decode on
   * {@link DECODE_LANE} (1 across all chains). A child cannot start before its parent, so declaring
   * the subtree early does not start it early.
   *
   * The chain activity is submitted *before* its children, so the parent gate applies to them —
   * but its `run` needs their promises, which exist only once they are submitted. Hence the deferred
   * `subtree` promise rather than an array that would still be empty when `run` first executes. The
   * two halves arrive separately because only the accounts decide the chain's verdict; the decode is
   * follow-on work with its own kind and row.
   *
   * The chain row is a `container`: it produces no data of its own, and the per-account children
   * carry the same kind and write their own ledger entries, so it must not claim freshness for the
   * chain on their behalf. The decode is declared alongside the accounts rather than run after
   * them, waiting on them through `deps` and settling as a no-op when they were all cancelled, so a
   * refresh has the same shape whether or not there turns out to be anything to decode.
   */
  const syncAndReDecodeEvents = async (
    chain: string,
    params: TransactionSyncParams,
    parent?: ActivityId,
  ): Promise<Result<void, TaskError>> => {
    const { accounts, type } = params;
    const chainId = chainSyncActivityId(chain);

    let declared!: (work: ChainSubtree) => void;
    const subtree = new Promise<ChainSubtree>((resolve) => {
      declared = resolve;
    });

    const chainWork = submitTask({
      container: true,
      id: chainId,
      kind: chainSyncActivity.kind,
      lane: chainSyncActivity.laneOf?.({ chain }),
      parent,
      rerunnable: false,
      run: async (): Promise<Result<void, TaskError>> => {
        logger.debug(`syncing ${chain} transactions for ${accounts.length} addresses`);
        const { accounts: accountWork, decode } = await subtree;
        const outcomes = await Promise.all(accountWork);
        await Promise.all(decode);
        return combineOutcomes(outcomes);
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.tx_sync.chain'), { chain: getChainName(chain) }),
      title: t('task_center.group.tx_sync'),
    });

    const accountWork = accounts.map(async account => syncTransactionTask(account, chainId));

    const decodeWork = TransactionChainTypeNeedDecoding.includes(type)
      ? [decodeTransactionsTask(chain, false, {
          deps: accounts.map(account => accountSyncActivityId(chain, account.address)),
          parent: chainId,
          skipWhen: () => accounts.every(wasCancelled),
        })]
      : [];

    declared({ accounts: accountWork, decode: decodeWork });

    return chainWork;
  };

  /**
   * Syncs a mixed set of accounts, one chain activity per chain they group into.
   *
   * @remarks
   * The account set is known synchronously, so every chain and every account below it is declared
   * in this one pass. There is no limiter of its own: {@link CHAIN_SYNC_LANE} caps how many chains
   * run at a time.
   */
  const syncTransactionsByChains = async (accounts: ChainAddress[], parent?: ActivityId): Promise<Result<void, TaskError>[]> => {
    logger.debug(`refreshing transactions for ${accounts.length} addresses`);

    return Promise.all(Object.entries(groupBy(accounts, item => item.chain))
      .map(async ([chain, chainAccounts]) => syncAndReDecodeEvents(chain, {
        accounts: chainAccounts,
        type: getTransactionTypeFromChain(chain),
      }, parent)));
  };

  return {
    syncAndReDecodeEvents,
    syncTransactionsByChains,
    syncTransactionTask,
  };
}

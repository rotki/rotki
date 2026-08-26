import { groupBy } from 'es-toolkit';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { hasTag } from 'plainfp/tagged';
import { msg } from '@/message-key';
import { logger } from '@/modules/core/common/logging/logging';
import { useSupportedChains } from '@/modules/core/common/use-supported-chains';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { combineOutcomes, isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useHistoryEventsApi } from '@/modules/history/api/events/use-history-events-api';
import { type BlockchainAddress, type ChainAddress, TransactionChainType, TransactionChainTypeNeedDecoding, type TransactionRequestPayload } from '@/modules/history/events/event-payloads';
import { accountSyncActivityId, chainSyncActivityId } from '@/modules/history/events/tx/sync-activity';
import { useHistoryTransactionAccounts } from '@/modules/history/events/tx/use-history-transaction-accounts';
import { useHistoryTransactionDecoding } from '@/modules/history/events/tx/use-history-transaction-decoding';
import { useTxQueryStatusStore } from '@/modules/history/use-tx-query-status-store';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ACCOUNT_SYNC_LANE_PREFIX, CHAIN_SYNC_LANE, familyLane } from '@/modules/task-center/core/orchestrator/spec';
import { type ActivityId, ActivityKind } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface TransactionSyncParams {
  accounts: ChainAddress[];
  type: TransactionChainType;
  trackProgress?: boolean;
}

/** A chain activity's declared children, split by whether they decide the chain's own outcome. */
interface ChainSubtree {
  readonly accounts: readonly Promise<Result<void, TaskError>>[];
  readonly decode: readonly Promise<void>[];
}

/**
 * The per-chain and per-account syncs report their outcome rather than swallowing it: a parent
 * settles on what its children actually did, and the sync's own error handling (status store,
 * notifications) still happens where the failure is, not at the caller.
 */
interface UseTransactionSyncReturn {
  syncAndReDecodeEvents: (chain: string, params: TransactionSyncParams, parent?: ActivityId) => Promise<Result<void, TaskError>>;
  syncTransactionTask: (account: ChainAddress, type: TransactionChainType, trackProgress?: boolean, parent?: ActivityId) => Promise<Result<void, TaskError>>;
  syncTransactionsByChains: (accounts: ChainAddress[], trackProgress?: boolean, parent?: ActivityId) => Promise<Result<void, TaskError>[]>;
}

export function useTransactionSync(): UseTransactionSyncReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notifyError } = useNotifications();
  const { fetchTransactionsTask } = useHistoryEventsApi();

  const { submitTask } = useNativeTask();
  const { isAddressCancelled, markAddressCancelled, markAddressFailed, removeQueryStatus, setEvmlikeStatus } = useTxQueryStatusStore();
  const { getChainName } = useSupportedChains();
  const { decodeTransactionsTask } = useHistoryTransactionDecoding();
  const { getTransactionTypeFromChain } = useHistoryTransactionAccounts();

  /**
   * A failed query leaves its address claiming to be querying unless something says otherwise.
   *
   * A skipped task is not a failure — it never ran, so a chain with no API key keeps its own
   * status. For a genuine failure nothing else moves the address on: the backend emits
   * `QUERYING_TRANSACTIONS_FINISHED` only on the success path and evmlike chains send no websocket
   * messages at all.
   *
   * Marked rather than removed: the panel's chain list is derived from these entries, so removing
   * one makes a fully-failed chain vanish with its denominator. `type` rides along so a synthesized
   * entry carries the right subtype instead of defaulting to evm.
   */
  const recordQueryFailure = (
    error: TaskError,
    account: ChainAddress,
    type: TransactionChainType,
    chainName: string,
  ): void => {
    if (hasTag(error, 'Skipped'))
      return;

    markAddressFailed(account, type);

    if (isActionable(error)) {
      notifyError(
        t('actions.transactions.error.title'),
        t('actions.transactions.error.description', {
          address: account.address,
          chain: chainName,
          error: error.message,
        }),
      );
    }
  };

  const syncTransactionTask = async (
    account: ChainAddress,
    type: TransactionChainType,
    trackProgress = true,
    parent?: ActivityId,
  ): Promise<Result<void, TaskError>> => {
    const { address, chain } = account;
    const isEvmlike = type === TransactionChainType.EVMLIKE;

    const blockchainAccount: BlockchainAddress = {
      address,
      blockchain: chain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    // Evmlike chains don't send websocket messages, so track status manually
    // Only track when progress display is enabled
    if (isEvmlike && trackProgress)
      setEvmlikeStatus(account, 'started');

    const chainName = getChainName(chain);
    // One native TX_SYNC activity per {chain, address}, on that chain's own lane so the family cap
    // gives two concurrent accounts *per chain*. Liveness, cancellation and re-run are the
    // orchestrator's; the chain grouping and the decode hand-off are in syncAndReDecodeEvents.
    const outcome = await submitTask({
      id: accountSyncActivityId(chain, address),
      kind: ActivityKind.TX_SYNC,
      lane: familyLane(ACCOUNT_SYNC_LANE_PREFIX, chain),
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
      const { error } = outcome;
      if (hasTag(error, 'BackendCancelled')) {
        logger.debug(error.message);
        removeQueryStatus(account);
      }
      else if (hasTag(error, 'Cancelled')) {
        markAddressCancelled(account);
      }
      else {
        recordQueryFailure(error, account, type, chainName);
      }
    }

    // Mark evmlike as finished when the task completes (but not when cancelled)
    // setEvmlikeStatus already guards against overwriting cancelled entries
    if (isEvmlike && trackProgress)
      setEvmlikeStatus(account, 'finished');

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
   */
  const syncAndReDecodeEvents = async (
    chain: string,
    params: TransactionSyncParams,
    parent?: ActivityId,
  ): Promise<Result<void, TaskError>> => {
    const { accounts, trackProgress = true, type } = params;
    const chainId = chainSyncActivityId(chain);

    let declared!: (work: ChainSubtree) => void;
    const subtree = new Promise<ChainSubtree>((resolve) => {
      declared = resolve;
    });

    const chainWork = submitTask({
      // Produces no data of its own — the per-account children carry the same kind and write their
      // own ledger entries, so this row must not claim freshness for the chain on their behalf.
      container: true,
      id: chainId,
      kind: ActivityKind.TX_SYNC,
      lane: CHAIN_SYNC_LANE,
      parent,
      rerunnable: false,
      run: async (): Promise<Result<void, TaskError>> => {
        logger.debug(`syncing ${chain} transactions for ${accounts.length} addresses`);
        const { accounts: accountWork, decode } = await subtree;
        // Both halves are already in flight, so awaiting them in sequence costs nothing and keeps
        // the verdict off the decode.
        const outcomes = await Promise.all(accountWork);
        await Promise.all(decode);
        return combineOutcomes(outcomes);
      },
      subtitle: activityLabelFor(msg.$t('task_center.activity.tx_sync.chain'), { chain: getChainName(chain) }),
      title: t('task_center.group.tx_sync'),
    });

    const accountWork = accounts.map(async account => syncTransactionTask(account, type, trackProgress, chainId));

    // Decoding is declared here rather than run at the end: it waits on every account of the chain
    // through `deps`, and completes as a no-op when they were all cancelled, so a refresh has the
    // same shape whether or not there turns out to be anything to decode.
    const decodeWork = TransactionChainTypeNeedDecoding.includes(type)
      ? [decodeTransactionsTask(chain, false, {
          deps: accounts.map(account => accountSyncActivityId(chain, account.address)),
          parent: chainId,
          skipWhen: () => accounts.every(account => isAddressCancelled(account)),
        })]
      : [];

    declared({ accounts: accountWork, decode: decodeWork });

    return chainWork;
  };

  const syncTransactionsByChains = async (accounts: ChainAddress[], trackProgress = true, parent?: ActivityId): Promise<Result<void, TaskError>[]> => {
    logger.debug(`refreshing transactions for ${accounts.length} addresses`);

    // The account set is known here, synchronously, so every chain and every account below it is
    // declared in this pass. No limiter: CHAIN_SYNC_LANE caps how many chains run at once.
    return Promise.all(Object.entries(groupBy(accounts, item => item.chain))
      .map(async ([chain, chainAccounts]) => syncAndReDecodeEvents(chain, {
        accounts: chainAccounts,
        trackProgress,
        type: getTransactionTypeFromChain(chain),
      }, parent)));
  };

  return {
    syncAndReDecodeEvents,
    syncTransactionsByChains,
    syncTransactionTask,
  };
}

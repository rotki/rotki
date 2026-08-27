import type { RunBackendTask } from '@/modules/task-center/use-native-task';
import { Blockchain } from '@rotki/common';
import { err, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { convertBtcBalances } from '@/modules/accounts/account-helpers';
import { useBlockchainAccountsStore } from '@/modules/accounts/use-blockchain-accounts-store';
import { useBlockchainBalancesApi } from '@/modules/balances/api/use-blockchain-balances-api';
import {
  BlockchainBalances,
  type BtcBalances,
  type FetchBlockchainBalancePayload,
} from '@/modules/balances/types/blockchain-balances';
import { useBalanceRefreshState } from '@/modules/balances/use-balance-refresh-state';
import { useBalancesStore } from '@/modules/balances/use-balances-store';
import { useBlockchainRefreshTimestampsStore } from '@/modules/balances/use-blockchain-refresh-timestamps-store';
import { isRequestCancellation } from '@/modules/core/api/request-queue/is-request-cancellation';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { Cancelled, isActionable, Skipped, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useBlockchainValidatorsStore } from '@/modules/staking/use-blockchain-validators-store';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

function isBtcBalances(data?: BtcBalances | any): data is BtcBalances {
  return !!data && (!!data.standalone || !!data.xpubs);
}

interface UseBalanceProcessingServiceReturn {
  /** Empties a chain's balances and marks it loaded. No backend task, so no activity involved. */
  clearChainBalances: (blockchain: string) => void;
  handleCachedFetch: (payload: FetchBlockchainBalancePayload, threshold: string | undefined) => Promise<Result<void, TaskError>>;
  handleRefresh: (runTask: RunBackendTask, payload: FetchBlockchainBalancePayload) => Promise<Result<void, TaskError>>;
  hasAccounts: (blockchain: string) => boolean;
  /** Whether the chain has anything to query — `hasAccounts`, except eth2. */
  shouldQuery: (blockchain: string) => boolean;
}

export function useBalanceProcessingService(): UseBalanceProcessingServiceReturn {
  const { notifyError } = useNotifications();
  const { queryBlockchainBalances, refreshBlockchainBalances, queryXpubBalances } = useBlockchainBalancesApi();
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { updateBalances } = useBalancesStore();
  const { isStale, updateTimestamps } = useBlockchainRefreshTimestampsStore();
  const { t } = useI18n({ useScope: 'global' });
  const { invalidate, markCompleted } = useTaskOrchestrator();
  const { isEth2Enabled } = useBlockchainValidatorsStore();
  const refreshState = useBalanceRefreshState();

  const processBalanceResult = (blockchain: string, parsedBalances: BlockchainBalances): void => {
    if (isStale(blockchain, parsedBalances.lastRefreshTs?.[blockchain]))
      return;

    if (parsedBalances.lastRefreshTs)
      updateTimestamps(parsedBalances.lastRefreshTs);

    const perAccount = parsedBalances.perAccount[blockchain];

    if (isBtcBalances(perAccount))
      updateBalances(blockchain, convertBtcBalances(blockchain, parsedBalances.totals, perAccount));
    else
      updateBalances(blockchain, parsedBalances);
  };

  const hasAccounts = (blockchain: string): boolean => {
    const account = get(accounts)[blockchain];
    return Boolean(account && account.length > 0);
  };

  /**
   * Whether this chain's account set is *known*, as opposed to merely absent.
   *
   * `fetchBlockchainAccounts` writes the key even when the chain has no accounts, so an empty
   * array means "fetched, genuinely empty" while a missing key means "not fetched yet". The
   * difference matters below: `hasAccounts` cannot tell them apart, and both read as false.
   */
  const accountsKnown = (blockchain: string): boolean => get(accounts)[blockchain] !== undefined;

  /**
   * Whether this chain has anything worth querying.
   *
   * eth2 is the exception, and it is one the backend already makes. Its "accounts" are
   * validators, produced by a backend task rather than an accounts read, so `hasAccounts` reads
   * false until that task lands — and a balance pass that overtakes it would skip the chain
   * entirely. The backend's `ChainsAggregator.query_balances` exempts `ETHEREUM_BEACONCHAIN` from
   * the same account check and routes it to `query_eth2_balances`, so a frontend gate that
   * disagrees only ever loses balances the backend would have returned.
   *
   * Gated on the module being active, which is the backend's own other precondition — with eth2
   * off there is nothing to query and the exemption must not apply.
   *
   * STOPGAP. The real shape is an edge from the validator fetch to the eth2 balance query, once
   * the refresh is a declared graph rather than a `Promise.all`. See the balances redesign plan.
   */
  const shouldQuery = (blockchain: string): boolean =>
    blockchain === Blockchain.ETH2 ? isEth2Enabled() : hasAccounts(blockchain);

  /**
   * Empties a chain's balances, for a chain that is known to have no accounts.
   *
   * @remarks
   * A chain whose accounts have not been read yet is left alone. Callers arrive through
   * `!hasAccounts(chain)`, which cannot tell "fetched, genuinely empty" from "not fetched yet" —
   * both read false — so acting on unknown *erases* balances whenever a refresh races the account
   * walk. An unknown chain keeps what it has until its accounts land.
   *
   * The completion is recorded here because a chain with no accounts submits no activity, so
   * nothing else would ever settle it and it would read as perpetually unloaded. That is only safe
   * below the guard above: recording completions while the account set is still unknown marks the
   * app "ever loaded" with no balances.
   */
  const clearChainBalances = (blockchain: string): void => {
    if (!accountsKnown(blockchain))
      return;

    updateBalances(blockchain, {
      perAccount: {},
      totals: {
        assets: {},
        liabilities: {},
      },
    });
    markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
  };

  /**
   * Whether this chain is worth asking about at all.
   *
   * SKIPPED with a reason, never `ok`. A chain with nothing to query is a real outcome the
   * user can be told about ("no accounts on this chain"), and reporting it as success recorded a
   * completion for work that never ran. It also keeps the chain in its run's denominator instead
   * of vanishing from it, so "11 of 17" counts every chain in scope rather than only the ones that
   * happened to have accounts.
   */
  const skipUnlessQueryable = (blockchain: string): Result<void, TaskError> | undefined => {
    if (shouldQuery(blockchain))
      return undefined;

    clearChainBalances(blockchain);
    return err(Skipped({ message: t('actions.balances.blockchain.skipped.no_accounts') }));
  };

  /**
   * Record one chain's outcome, whichever layer produced it.
   *
   * Both layers land here so the ledger is written in exactly one place: the network query owns its
   * result through a backend task, the cache-only read resolves directly, and neither difference
   * reaches the bookkeeping.
   */
  const settleChain = (
    blockchain: string,
    result: Result<BlockchainBalances, TaskError>,
    notify: boolean,
  ): Result<void, TaskError> => {
    if (isErr(result)) {
      if (isActionable(result.error)) {
        logger.error(result.error.message);
        if (notify) {
          notifyError(
            t('actions.balances.blockchain.error.title'),
            t('actions.balances.blockchain.error.description', {
              error: result.error.message,
            }),
          );
        }
      }
      invalidate(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
    }
    else {
      processBalanceResult(blockchain, result.value);
      markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
    }

    return mapResult(result, () => {});
  };

  const executeBalanceQuery = async (
    runTask: RunBackendTask,
    blockchain: string,
    apiCall: () => Promise<{ taskId: number }>,
  ): Promise<Result<void, TaskError>> => {
    const skipped = skipUnlessQueryable(blockchain);
    if (skipped)
      return skipped;

    // `runTask` types the payload but does not validate it — the schema is only applied here.
    return settleChain(
      blockchain,
      mapResult(await runTask<unknown>(apiCall), result => BlockchainBalances.parse(result)),
      true,
    );
  };

  /**
   * Layer 1's read. A plain cache-only GET, so its outcome is a rejection rather than a task result
   * — the only difference from {@link executeBalanceQuery}, and it ends at the same bookkeeping.
   */
  const handleCachedFetch = async (
    payload: FetchBlockchainBalancePayload,
    threshold: string | undefined,
  ): Promise<Result<void, TaskError>> => {
    const { blockchain } = payload;
    const skipped = skipUnlessQueryable(blockchain);
    if (skipped)
      return skipped;

    let result: Result<BlockchainBalances, TaskError>;
    try {
      result = ok(await queryBlockchainBalances(payload, threshold));
    }
    catch (error: unknown) {
      result = err(isRequestCancellation(error)
        ? Cancelled({ message: t('actions.balances.blockchain.cancelled') })
        : TaskFailed({ cause: error, message: getErrorMessage(error) }));
    }

    return settleChain(blockchain, result, false);
  };

  const handleRefresh = async (
    runTask: RunBackendTask,
    payload: FetchBlockchainBalancePayload,
  ): Promise<Result<void, TaskError>> => {
    const { blockchain, isXpub } = payload;
    refreshState.start(blockchain);
    try {
      return await executeBalanceQuery(
        runTask,
        blockchain,
        async () => !isXpub ? refreshBlockchainBalances(payload) : queryXpubBalances(payload),
      );
    }
    finally {
      refreshState.stop(blockchain);
    }
  };

  return {
    clearChainBalances,
    handleCachedFetch,
    handleRefresh,
    hasAccounts,
    shouldQuery,
  };
}

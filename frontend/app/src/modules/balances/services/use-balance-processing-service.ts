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

  const processBalanceResult = (blockchain: string, result: unknown): void => {
    const parsedBalances: BlockchainBalances = BlockchainBalances.parse(result);

    // 🔴 Drop a payload older than what this chain already holds. A data refresh from the DB and a
    // network query are allowed to overlap by design, so the two can land out of order; without
    // this the slower one wins and rolls the chain back to stale balances. Discarding by age is
    // what makes the overlap harmless — and what lets the work stop being serialised to avoid it.
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
   * ⭐ eth2 is the exception, and it is one the backend already makes. Its "accounts" are
   * validators, produced by a backend task rather than an accounts read, so `hasAccounts` reads
   * false until that task lands — and a balance pass that overtakes it would skip the chain
   * entirely. `aggregator.py:727` exempts `ETHEREUM_BEACONCHAIN` from the same account check and
   * routes it to `query_eth2_balances`, so the frontend gate disagreeing with it only ever loses
   * balances the backend would have returned.
   *
   * Gated on the module being active, which is the backend's own other precondition — with eth2
   * off there is nothing to query and the exemption must not apply.
   *
   * ⚠️ STOPGAP. The real shape is an edge from the validator fetch to the eth2 balance query, once
   * the refresh is a declared graph rather than a `Promise.all`. See the balances redesign plan.
   */
  const shouldQuery = (blockchain: string): boolean =>
    blockchain === Blockchain.ETH2 ? isEth2Enabled() : hasAccounts(blockchain);

  const clearChainBalances = (blockchain: string): void => {
    // 🔴 A chain whose accounts have not been read yet is left alone. Every caller arrives here
    // through `!hasAccounts(chain)`, and that cannot tell "fetched, genuinely empty" from "not
    // fetched yet" — both read false. So clearing on unknown *erases* a chain's balances whenever
    // a refresh races the account walk, rather than merely skipping it. Only a known-empty chain
    // is cleared; an unknown one keeps whatever it has until its accounts land.
    if (!accountsKnown(blockchain))
      return;

    updateBalances(blockchain, {
      perAccount: {},
      totals: {
        assets: {},
        liabilities: {},
      },
    });
    // No accounts means no activity was submitted, so nothing would otherwise record that this
    // chain is settled. Without it an empty chain reads as perpetually unloaded.
    //
    // Safe here because the early return above has already established the account set is known: a
    // refresh racing the accounts fetch used to see every chain as empty, and recording completions
    // there marked the whole app "ever loaded" with no balances — dropping the initial-loading
    // state while the real data was still coming.
    markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
  };

  const executeBalanceQuery = async (
    runTask: RunBackendTask,
    blockchain: string,
    apiCall: () => Promise<{ taskId: number }>,
    notify: boolean = true,
  ): Promise<Result<void, TaskError>> => {
    // 🔴🔴 SKIPPED with a reason, never `ok`. A chain with nothing to query is a real outcome the
    // user can be told about ("no accounts on this chain"), and reporting it as success recorded a
    // completion for work that never ran. §5 is the other half of the argument: the chain stays in
    // its run's denominator instead of vanishing from it, so "11 of 17" counts every chain in scope
    // rather than only the ones that happened to have accounts.
    if (!shouldQuery(blockchain)) {
      clearChainBalances(blockchain);
      return err(Skipped({ message: t('actions.balances.blockchain.skipped.no_accounts') }));
    }

    const result = await runTask<BlockchainBalances>(apiCall);

    if (isErr(result)) {
      if (isActionable(result.error)) {
        logger.error(result.error.message);
        // ⭐ `notify` is off for the hydration read. A data refresh from the DB retries silently —
        // it is plumbing, not something the user asked for and can act on — and a notification per
        // attempt would make one failing chain raise three toasts. The log stays either way, so a
        // chain that never hydrates is still diagnosable.
        if (notify) {
          notifyError(
            t('actions.balances.blockchain.error.title'),
            t('actions.balances.blockchain.error.description', {
              error: result.error.message,
            }),
          );
        }
      }
      // Forget any earlier success for this chain, so a failed query reads as "no data" rather
      // than leaving the last good load standing. Runs before the activity settles, so the FAILED
      // record it writes has no sticky `lastSuccessAt` to inherit.
      invalidate(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
    }
    else {
      processBalanceResult(blockchain, result.value);
      // The activity's own completion would say the same, but only for the id it ran under; the
      // service is what knows the chain has data, whichever of the two ids fetched it.
      markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
    }

    return mapResult(result, () => {});
  };

  const handleCachedFetch = async (
    payload: FetchBlockchainBalancePayload,
    threshold: string | undefined,
  ): Promise<Result<void, TaskError>> => {
    const { blockchain } = payload;
    if (!shouldQuery(blockchain)) {
      clearChainBalances(blockchain);
      return err(Skipped({ message: t('actions.balances.blockchain.skipped.no_accounts') }));
    }

    try {
      processBalanceResult(blockchain, await queryBlockchainBalances(payload, threshold));
      markCompleted(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
      return ok(undefined);
    }
    catch (error: unknown) {
      const taskError = isRequestCancellation(error)
        ? Cancelled({ message: 'Request cancelled' })
        : TaskFailed({ cause: error, message: getErrorMessage(error) });
      if (isActionable(taskError))
        logger.error(taskError.message);

      invalidate(ActivityKind.BLOCKCHAIN_BALANCES, blockchain);
      return err(taskError);
    }
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

import type { RunBackendTask } from '@/modules/task-center/use-native-task';
import { isErr, map as mapResult, ok, type Result } from 'plainfp/result';
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
import { logger } from '@/modules/core/common/logging/logging';
import { useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { ActivityKind } from '@/modules/task-center/core/types';
import { useTaskOrchestrator } from '@/modules/task-center/use-task-orchestrator';

function isBtcBalances(data?: BtcBalances | any): data is BtcBalances {
  return !!data && (!!data.standalone || !!data.xpubs);
}

interface UseBalanceProcessingServiceReturn {
  /** Empties a chain's balances and marks it loaded. No backend task, so no activity involved. */
  clearChainBalances: (blockchain: string) => void;
  handleCachedFetch: (runTask: RunBackendTask, payload: FetchBlockchainBalancePayload, threshold: string | undefined) => Promise<Result<void, TaskError>>;
  handleRefresh: (runTask: RunBackendTask, payload: FetchBlockchainBalancePayload) => Promise<Result<void, TaskError>>;
  hasAccounts: (blockchain: string) => boolean;
}

export function useBalanceProcessingService(): UseBalanceProcessingServiceReturn {
  const { notifyError } = useNotifications();
  const { queryBlockchainBalances, refreshBlockchainBalances, queryXpubBalances } = useBlockchainBalancesApi();
  const { accounts } = storeToRefs(useBlockchainAccountsStore());
  const { updateBalances } = useBalancesStore();
  const { updateTimestamps } = useBlockchainRefreshTimestampsStore();
  const { t } = useI18n({ useScope: 'global' });
  const { invalidate, markCompleted } = useTaskOrchestrator();
  const refreshState = useBalanceRefreshState();

  const processBalanceResult = (blockchain: string, result: unknown): void => {
    const parsedBalances: BlockchainBalances = BlockchainBalances.parse(result);

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
  ): Promise<Result<void, TaskError>> => {
    if (!hasAccounts(blockchain)) {
      clearChainBalances(blockchain);
      return ok(undefined);
    }

    const result = await runTask<BlockchainBalances>(apiCall);

    if (isErr(result)) {
      if (isActionable(result.error)) {
        logger.error(result.error.message);
        notifyError(
          t('actions.balances.blockchain.error.title'),
          t('actions.balances.blockchain.error.description', {
            error: result.error.message,
          }),
        );
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
    runTask: RunBackendTask,
    payload: FetchBlockchainBalancePayload,
    threshold: string | undefined,
  ): Promise<Result<void, TaskError>> => {
    const { blockchain } = payload;
    return executeBalanceQuery(runTask, blockchain, async () => queryBlockchainBalances(payload, threshold));
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
  };
}

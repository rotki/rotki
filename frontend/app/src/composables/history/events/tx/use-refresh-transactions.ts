import type { RefreshTransactionsParams } from './types';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useRefreshHandlers } from '@/composables/history/events/tx/refresh-handlers';
import { useAccountCategorization } from '@/composables/history/events/tx/use-account-categorization';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useTransactionSync } from '@/composables/history/events/tx/use-transaction-sync';
import { useStatusUpdater } from '@/composables/status';
import { useHistoryStore } from '@/store/history';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useHistoryRefreshStateStore } from '@/store/history/refresh-state';
import { useSessionSettingsStore } from '@/store/settings/session';
import { type ChainAddress, TransactionChainType } from '@/types/history/events';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Section, Status } from '@/types/status';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';

interface UseRefreshTransactionsReturn {
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
}

export function useRefreshTransactions(): UseRefreshTransactionsReturn {
  const queue = new LimitedParallelizationQueue(1);

  const { initializeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();
  const { initializeQueryStatus: initializeExchangeEventsQueryStatus, resetQueryStatus: resetExchangesQueryStatus } = useEventsQueryStatusStore();
  const { getBitcoinAccounts, getEvmAccounts, getEvmLikeAccounts, getSolanaAccounts } = useHistoryTransactionAccounts();
  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY);
  const { fetchUndecodedTransactionsBreakdown, fetchUndecodedTransactionsStatus } = useHistoryTransactionDecoding();
  const { resetUndecodedTransactionsStatus } = useHistoryStore();

  const { syncTransactionsByChains } = useTransactionSync();
  const { categorizeAccountsByType } = useAccountCategorization();
  const { queryAllExchangeEvents, queryOnlineEvent } = useRefreshHandlers();

  const {
    addPendingAccounts,
    finishRefresh,
    getNewAccounts,
    getPendingAccountsForRefresh,
    hasPendingAccounts,
    isRefreshing,
    shouldRefreshAll,
    startRefresh,
  } = useHistoryRefreshStateStore();

  const getAllAccountsByType = (chains: string[]): ReturnType<typeof categorizeAccountsByType> => ({
    bitcoinAccounts: getBitcoinAccounts(chains),
    evmAccounts: getEvmAccounts(chains),
    evmLikeAccounts: getEvmLikeAccounts(chains),
    solanaAccounts: getSolanaAccounts(chains),
  });

  const combineAccounts = (categorized: ReturnType<typeof categorizeAccountsByType>): ChainAddress[] => [
    ...categorized.evmAccounts,
    ...categorized.evmLikeAccounts,
    ...categorized.bitcoinAccounts,
    ...categorized.solanaAccounts,
  ];

  const refreshTransactions = async (params: RefreshTransactionsParams = {}): Promise<void> => {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    const { accounts, exchanges, queries } = payload;
    const fullRefresh = Object.keys(payload).length === 0;

    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

    // Determine initial accounts to check
    let categorized = accounts?.length
      ? categorizeAccountsByType(accounts)
      : fullRefresh
        ? getAllAccountsByType(chains)
        : { bitcoinAccounts: [], evmAccounts: [], evmLikeAccounts: [], solanaAccounts: [] };

    const allCurrentAccounts = combineAccounts(categorized);
    const newAccountsList = getNewAccounts(allCurrentAccounts);
    const hasNewAccounts = newAccountsList.length > 0;

    // Skip refresh only if fetchDisabled returns true AND there are no new accounts
    if (fetchDisabled(userInitiated) && !hasNewAccounts)
      return;

    // If refresh is already running, add new accounts to pending
    if (get(isRefreshing)) {
      if (newAccountsList.length > 0)
        addPendingAccounts(newAccountsList);
      return;
    }

    // Determine final accounts to refresh
    if (fullRefresh && shouldRefreshAll(allCurrentAccounts)) {
      categorized = getAllAccountsByType(chains);
    }
    else if (hasNewAccounts) {
      categorized = categorizeAccountsByType(newAccountsList);
    }

    const { bitcoinAccounts, evmAccounts, evmLikeAccounts, solanaAccounts } = categorized;
    const accountsToRefresh = combineAccounts(categorized);

    if (accountsToRefresh.length > 0) {
      startRefresh(accountsToRefresh);
      setStatus(Status.REFRESHING);
      initializeQueryStatus(evmAccounts);
      resetUndecodedTransactionsStatus();
    }
    else {
      resetQueryStatus();
    }

    try {
      if (!disableEvmEvents && (fullRefresh || evmAccounts.length > 0))
        await fetchUndecodedTransactionsStatus();

      const asyncOperations: Promise<void>[] = [];

      // Queue transaction syncing for each account type
      [
        { accounts: evmAccounts, type: TransactionChainType.EVM },
        { accounts: bitcoinAccounts, type: TransactionChainType.BITCOIN },
        { accounts: evmLikeAccounts, type: TransactionChainType.EVMLIKE },
        { accounts: solanaAccounts, type: TransactionChainType.SOLANA },
      ].forEach(({ accounts, type }) => {
        if (accounts.length > 0)
          asyncOperations.push(syncTransactionsByChains({ accounts, type }));
      });

      if (fullRefresh || disableEvmEvents || exchanges) {
        initializeExchangeEventsQueryStatus(exchanges || get(connectedExchanges));
        asyncOperations.push(queryAllExchangeEvents(exchanges));
      }
      else {
        resetExchangesQueryStatus();
      }

      const queriesToExecute: OnlineHistoryEventsQueryType[] | undefined = fullRefresh || disableEvmEvents
        ? [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS, OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS]
        : queries;

      queriesToExecute?.forEach(query => asyncOperations.push(queryOnlineEvent(query)));

      for (const operation of asyncOperations) {
        try {
          await operation;
        }
        catch (error: any) {
          logger.error(error);
        }
      }

      queue.queue('fetch-undecoded-transactions-breakdown', fetchUndecodedTransactionsBreakdown);

      if (!disableEvmEvents && evmAccounts.length > 0)
        queue.queue('undecoded-transactions-status-final', fetchUndecodedTransactionsStatus);
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
    finally {
      finishRefresh();
    }

    // After refresh is complete, check if there are pending accounts to refresh
    if (!get(hasPendingAccounts))
      return;

    const pendingAccounts = getPendingAccountsForRefresh();
    // Recursively call refreshTransactions to handle pending accounts
    setTimeout(() => {
      refreshTransactions({
        ...params,
        payload: {
          ...params.payload,
          accounts: pendingAccounts,
        },
      }).catch(error => logger.error('Failed to refresh pending accounts', error));
    }, 100);
  };

  return {
    refreshTransactions,
  };
}

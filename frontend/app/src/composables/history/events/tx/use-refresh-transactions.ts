import type { RefreshTransactionsParams } from './types';
import type { Exchange } from '@/types/exchanges';
import type { ChainAddress } from '@/types/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useRefreshHandlers } from '@/composables/history/events/tx/refresh-handlers';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useTransactionSync } from '@/composables/history/events/tx/use-transaction-sync';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useHistoryStore } from '@/store/history';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useHistoryRefreshStateStore } from '@/store/history/refresh-state';
import { useSessionSettingsStore } from '@/store/settings/session';
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
  const { getAllAccounts } = useHistoryTransactionAccounts();
  const { fetchDisabled, isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY);
  const { fetchUndecodedTransactionsBreakdown, fetchUndecodedTransactionsStatus } = useHistoryTransactionDecoding();
  const { resetUndecodedTransactionsStatus } = useHistoryStore();
  const { isDecodableChains } = useSupportedChains();

  const { syncTransactionsByChains } = useTransactionSync();
  const { queryAllExchangeEvents, queryOnlineEvent } = useRefreshHandlers();

  const {
    addPendingAccounts,
    addPendingExchanges,
    finishRefresh,
    getNewAccounts,
    getNewExchanges,
    getPendingAccountsForRefresh,
    getPendingExchangesForRefresh,
    hasPendingAccounts,
    hasPendingExchanges,
    isRefreshing,
    startRefresh,
  } = useHistoryRefreshStateStore();

  const refreshTransactions = async (params: RefreshTransactionsParams = {}): Promise<void> => {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    const { accounts, exchanges, queries } = payload;
    const fullRefresh = Object.keys(payload).length === 0;

    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

    // Determine initial accounts to check
    const allCurrentAccounts = accounts?.length
      ? accounts
      : fullRefresh
        ? getAllAccounts(chains)
        : [];

    const newAccountsList = getNewAccounts(allCurrentAccounts);
    const hasNewAccounts = newAccountsList.length > 0;

    // Check for new exchanges
    const allCurrentExchanges = exchanges || get(connectedExchanges);
    const newExchangesList = getNewExchanges(allCurrentExchanges);
    const hasNewExchanges = newExchangesList.length > 0;

    // Skip refresh only if fetchDisabled returns true AND there are no new accounts or exchanges
    if (fetchDisabled(userInitiated) && !hasNewAccounts && !hasNewExchanges)
      return;

    setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);

    // If refresh is already running, add new accounts/exchanges to pending
    if (get(isRefreshing)) {
      if (newAccountsList.length > 0)
        addPendingAccounts(newAccountsList);
      if (newExchangesList.length > 0)
        addPendingExchanges(newExchangesList);
      return;
    }

    // Determine final accounts and exchanges to refresh
    let accountsToRefresh: ChainAddress[] = [];
    let exchangesToRefresh: Exchange[] = [];

    if (fullRefresh) {
      // Only refresh all accounts if there are new accounts
      // If only exchanges are new, don't refresh accounts
      if (hasNewAccounts || userInitiated) {
        accountsToRefresh = getAllAccounts(chains);
      }
      exchangesToRefresh = get(connectedExchanges);
    }
    else if (hasNewAccounts || hasNewExchanges) {
      if (hasNewAccounts)
        accountsToRefresh = newAccountsList;
      if (hasNewExchanges)
        exchangesToRefresh = newExchangesList;
    }
    else if (accounts?.length || exchanges) {
      accountsToRefresh = accounts || [];
      exchangesToRefresh = exchanges || [];
    }

    // Get decodable accounts for query status initialization
    const decodableAccounts = accountsToRefresh.filter(account => isDecodableChains(account.chain));

    if (accountsToRefresh.length > 0 || exchangesToRefresh.length > 0) {
      startRefresh(accountsToRefresh, exchangesToRefresh);
      if (accountsToRefresh.length > 0) {
        initializeQueryStatus(decodableAccounts);
        resetUndecodedTransactionsStatus();
      }
    }
    else {
      resetQueryStatus();
    }

    try {
      if (fullRefresh || decodableAccounts.length > 0)
        await fetchUndecodedTransactionsStatus();

      const asyncOperations: Promise<void>[] = [];

      // Sync transactions for all accounts (type is derived from chain inside syncTransactionsByChains)
      if (accountsToRefresh.length > 0)
        asyncOperations.push(syncTransactionsByChains(accountsToRefresh));

      if (fullRefresh || exchanges) {
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

      if (decodableAccounts.length > 0)
        queue.queue('undecoded-transactions-status-final', fetchUndecodedTransactionsStatus);
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
    finally {
      finishRefresh();
      setStatus(Status.LOADED);
    }

    // After refresh is complete, check if there are pending accounts or exchanges to refresh
    const hasPending = get(hasPendingAccounts) || get(hasPendingExchanges);
    if (!hasPending)
      return;

    const pendingAccounts = getPendingAccountsForRefresh();
    const pendingExchanges = getPendingExchangesForRefresh();

    // Recursively call refreshTransactions to handle pending accounts/exchanges
    setTimeout(() => {
      refreshTransactions({
        ...params,
        payload: {
          ...params.payload,
          accounts: pendingAccounts.length > 0 ? pendingAccounts : undefined,
          exchanges: pendingExchanges.length > 0 ? pendingExchanges : undefined,
        },
      }).catch(error => logger.error('Failed to refresh pending accounts/exchanges', error));
    }, 100);
  };

  return {
    refreshTransactions,
  };
}

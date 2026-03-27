import type { RefreshTransactionsParams } from './types';
import type { Exchange } from '@/types/exchanges';
import type { ChainAddress } from '@/types/history/events';
import { startPromise } from '@shared/utils';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useRefreshHandlers } from '@/composables/history/events/tx/refresh-handlers';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useTransactionSync } from '@/composables/history/events/tx/use-transaction-sync';
import { useSupportedChains } from '@/composables/info/chains';
import { useSchedulerState } from '@/composables/session/use-scheduler-state';
import { Section, Status, useStatusUpdater } from '@/composables/status';
import { useExchangeData } from '@/modules/balances/exchanges/use-exchange-data';
import { useDecodingStatusStore } from '@/modules/history/use-decoding-status-store';
import { sigilBus } from '@/modules/sigil/event-bus';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useHistoryRefreshStateStore } from '@/store/history/refresh-state';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';

interface NoveltyDetection {
  newAccounts: ChainAddress[];
  newExchanges: Exchange[];
}

interface RefreshTargets {
  accounts: ChainAddress[];
  decodableAccounts: ChainAddress[];
  exchanges: Exchange[];
  fullRefresh: boolean;
  queryExchanges: boolean;
  shouldShowSyncProgress: boolean;
  usedExchanges: Exchange[];
}

interface UseRefreshTransactionsReturn {
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
}

export function useRefreshTransactions(): UseRefreshTransactionsReturn {
  let timeout: NodeJS.Timeout;
  const queue = new LimitedParallelizationQueue(1);

  const { initializeQueryStatus, resetQueryStatus, stopSyncing: stopTxSyncing } = useTxQueryStatusStore();
  const { initializeQueryStatus: initializeExchangeEventsQueryStatus, resetQueryStatus: resetExchangesQueryStatus, stopSyncing: stopEventsSyncing } = useEventsQueryStatusStore();
  const { getAllAccounts } = useHistoryTransactionAccounts();
  const { fetchDisabled, isFirstLoad, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY);
  const { fetchUndecodedTransactionsBreakdown, fetchUndecodedTransactionsStatus } = useHistoryTransactionDecoding();
  const { resetDecodingSyncProgress, resetUndecodedTransactionsStatus, stopDecodingSyncProgress } = useDecodingStatusStore();
  const { isDecodableChains } = useSupportedChains();

  const { syncTransactionsByChains, waitForDecoding } = useTransactionSync();
  const { queryAllExchangeEvents, queryOnlineEvent } = useRefreshHandlers();
  const { onHistoryFinished, onHistoryStarted } = useSchedulerState();

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

  const { syncingExchanges, isSameExchange } = useExchangeData();

  function filterSyncingExchanges(exchanges: Exchange[] | undefined): Exchange[] {
    return exchanges
      ? exchanges.filter(exchange => get(syncingExchanges).some(syncing => isSameExchange(syncing, exchange)))
      : get(syncingExchanges);
  }

  function resolveInputAccounts(accounts: ChainAddress[] | undefined, fullRefresh: boolean, chains: string[]): ChainAddress[] {
    if (accounts?.length)
      return accounts;
    if (fullRefresh)
      return getAllAccounts(chains);
    return [];
  }

  function detectNovelty(allAccounts: ChainAddress[], usedExchanges: Exchange[]): NoveltyDetection {
    return {
      newAccounts: getNewAccounts(allAccounts),
      newExchanges: getNewExchanges(usedExchanges),
    };
  }

  function resolveForFullRefresh(novelty: NoveltyDetection, chains: string[], userInitiated: boolean): { accounts: ChainAddress[]; exchanges: Exchange[] } {
    return {
      accounts: (novelty.newAccounts.length > 0 || userInitiated) ? getAllAccounts(chains) : [],
      exchanges: get(syncingExchanges),
    };
  }

  function resolveForNovelItems(novelty: NoveltyDetection): { accounts: ChainAddress[]; exchanges: Exchange[] } {
    return {
      accounts: novelty.newAccounts.length > 0 ? novelty.newAccounts : [],
      exchanges: novelty.newExchanges.length > 0 ? novelty.newExchanges : [],
    };
  }

  function resolveRefreshTargets(
    payload: { accounts?: ChainAddress[]; exchanges?: Exchange[] },
    novelty: NoveltyDetection,
    opts: { chains: string[]; fullRefresh: boolean; usedExchanges: Exchange[]; userInitiated: boolean },
  ): RefreshTargets {
    const { chains, fullRefresh, usedExchanges, userInitiated } = opts;
    const hasNovelty = novelty.newAccounts.length > 0 || novelty.newExchanges.length > 0;

    let resolved: { accounts: ChainAddress[]; exchanges: Exchange[] };

    if (fullRefresh)
      resolved = resolveForFullRefresh(novelty, chains, userInitiated);
    else if (hasNovelty)
      resolved = resolveForNovelItems(novelty);
    else
      resolved = { accounts: payload.accounts || [], exchanges: payload.exchanges || [] };

    return {
      accounts: resolved.accounts,
      decodableAccounts: resolved.accounts.filter(account => isDecodableChains(account.chain)),
      exchanges: resolved.exchanges,
      fullRefresh,
      queryExchanges: fullRefresh || !!payload.exchanges,
      shouldShowSyncProgress: isFirstLoad() || hasNovelty,
      usedExchanges,
    };
  }

  function initializeRefresh(targets: RefreshTargets): void {
    resetQueryStatus();

    if (!(targets.accounts.length > 0 || targets.exchanges.length > 0)) {
      return;
    }

    startRefresh(targets.accounts, targets.exchanges);
    onHistoryStarted();

    if (!(targets.accounts.length > 0 && targets.shouldShowSyncProgress)) {
      return;
    }

    initializeQueryStatus(targets.decodableAccounts);
    resetUndecodedTransactionsStatus();
    resetDecodingSyncProgress();
  }

  function resolveOnlineQueries(
    targets: RefreshTargets,
    disableEvmEvents: boolean,
    queries: OnlineHistoryEventsQueryType[] | undefined,
  ): OnlineHistoryEventsQueryType[] {
    if (targets.fullRefresh || disableEvmEvents)
      return [OnlineHistoryEventsQueryType.ETH_WITHDRAWALS, OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS];
    return queries || [];
  }

  async function executeOperations(
    targets: RefreshTargets,
    disableEvmEvents: boolean,
    queries: OnlineHistoryEventsQueryType[] | undefined,
  ): Promise<void> {
    if (targets.fullRefresh || targets.decodableAccounts.length > 0)
      await fetchUndecodedTransactionsStatus();

    const asyncOperations: Promise<void>[] = [];

    if (targets.accounts.length > 0)
      asyncOperations.push(syncTransactionsByChains(targets.accounts, targets.shouldShowSyncProgress));

    resetExchangesQueryStatus();

    if (targets.queryExchanges) {
      if (targets.shouldShowSyncProgress)
        initializeExchangeEventsQueryStatus(targets.usedExchanges);
      asyncOperations.push(queryAllExchangeEvents(targets.usedExchanges));
    }

    for (const query of resolveOnlineQueries(targets, disableEvmEvents, queries))
      asyncOperations.push(queryOnlineEvent(query));

    for (const operation of asyncOperations) {
      try {
        await operation;
      }
      catch (error: unknown) {
        logger.error(error);
      }
    }

    // Wait for any queued decode tasks to finish before proceeding,
    // so that WS progress updates are not dropped by stopDecodingSyncProgress()
    await waitForDecoding();

    queue.queue('fetch-undecoded-transactions-breakdown', fetchUndecodedTransactionsBreakdown);

    if (targets.decodableAccounts.length > 0)
      queue.queue('undecoded-transactions-status-final', fetchUndecodedTransactionsStatus);
  }

  function drainPending(params: RefreshTransactionsParams): void {
    if (!get(hasPendingAccounts) && !get(hasPendingExchanges))
      return;

    const pendingAccounts = getPendingAccountsForRefresh();
    const pendingExchanges = getPendingExchangesForRefresh();

    timeout = setTimeout(() => {
      startPromise(refreshTransactions({
        ...params,
        payload: {
          ...params.payload,
          accounts: pendingAccounts.length > 0 ? pendingAccounts : undefined,
          exchanges: pendingExchanges.length > 0 ? pendingExchanges : undefined,
        },
      }));
    }, 100);
  }

  function processNoveltyDetection({ newAccounts, newExchanges }: NoveltyDetection): void {
    if (newAccounts.length > 0)
      addPendingAccounts(newAccounts);
    if (newExchanges.length > 0)
      addPendingExchanges(newExchanges);
  }

  function shouldNotRefresh(userInitiated: boolean, { newAccounts, newExchanges }: NoveltyDetection): boolean {
    return fetchDisabled(userInitiated) && newAccounts.length === 0 && newExchanges.length === 0;
  }

  async function refreshTransactions(params: RefreshTransactionsParams = {}): Promise<void> {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    const fullRefresh = Object.keys(payload).length === 0;

    const usedExchanges = filterSyncingExchanges(payload.exchanges);
    const allCurrentAccounts = resolveInputAccounts(payload.accounts, fullRefresh, chains);
    const novelty = detectNovelty(allCurrentAccounts, usedExchanges);

    if (shouldNotRefresh(userInitiated, novelty))
      return;

    setStatus(isFirstLoad() ? Status.LOADING : Status.REFRESHING);

    if (get(isRefreshing)) {
      processNoveltyDetection(novelty);
      return;
    }

    const targets = resolveRefreshTargets(payload, novelty, {
      chains,
      fullRefresh,
      usedExchanges,
      userInitiated,
    });

    initializeRefresh(targets);

    try {
      await executeOperations(targets, disableEvmEvents, payload.queries);
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
    finally {
      finishRefresh();
      setStatus(Status.LOADED);
      onHistoryFinished();
      stopTxSyncing();
      stopEventsSyncing();
      stopDecodingSyncProgress();
      sigilBus.emit('history:ready');
    }

    drainPending(params);
  }

  onScopeDispose(() => {
    if (timeout)
      clearTimeout(timeout);
  });

  return {
    refreshTransactions,
  };
}

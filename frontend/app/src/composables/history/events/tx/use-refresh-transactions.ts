import type { RefreshTransactionsParams, TransactionSyncParams } from './types';
import { groupBy } from 'es-toolkit';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useRefreshHandlers } from '@/composables/history/events/tx/refresh-handlers';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useStatusUpdater } from '@/composables/status';
import { useHistoryStore } from '@/store/history';
import { useEventsQueryStatusStore } from '@/store/history/query-status/events-query-status';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useHistoryRefreshStateStore } from '@/store/history/refresh-state';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import {
  type BlockchainAddress,
  type ChainAddress,
  TransactionChainType,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Section, Status } from '@/types/status';
import { BackendCancelledTaskError, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';

interface UseRefreshTransactionsReturn {
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
}

export function useRefreshTransactions(): UseRefreshTransactionsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(1);
  const { fetchTransactionsTask } = useHistoryEventsApi();

  const { awaitTask, isTaskRunning } = useTaskStore();
  const { initializeQueryStatus, removeQueryStatus, resetQueryStatus } = useTxQueryStatusStore();
  const { initializeQueryStatus: initializeExchangeEventsQueryStatus, resetQueryStatus: resetExchangesQueryStatus } = useEventsQueryStatusStore();
  const { getChainName, isBtcChains, isEvmLikeChains } = useSupportedChains();
  const { getBitcoinAccounts, getEvmAccounts, getEvmLikeAccounts } = useHistoryTransactionAccounts();
  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY);
  const {
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
  } = useHistoryTransactionDecoding();
  const { resetUndecodedTransactionsStatus } = useHistoryStore();

  const syncTransactionTask = async (
    account: ChainAddress,
    type: TransactionChainType,
  ): Promise<void> => {
    const taskType = TaskType.TX;
    const { address, chain } = account;

    const blockchainAccount: BlockchainAddress = {
      address,
      blockchain: chain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    const chainName = get(getChainName(chain));
    const { taskId } = await fetchTransactionsTask(defaults);
    const taskMeta = {
      address,
      chain,
      description: t('actions.transactions.task.description', {
        address,
        chain: chainName,
      }),
      title: t('actions.transactions.task.title'),
      type,
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (error instanceof BackendCancelledTaskError) {
        logger.debug(error);
        removeQueryStatus(account);
      }
      else if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.transactions.error.description', {
            address,
            chain: chainName,
            error,
          }),
          title: t('actions.transactions.error.title'),
        });
      }
    }
    finally {
      setStatus(isTaskRunning(taskType, { type }) ? Status.REFRESHING : Status.LOADED);
    }
  };

  const syncAndReDecodeEvents = async (
    chain: string,
    params: TransactionSyncParams,
  ): Promise<void> => {
    const { accounts, type } = params;
    logger.debug(`syncing ${chain} transactions for ${accounts.length} addresses`);
    const isBitcoin = type === TransactionChainType.BITCOIN;

    const getAccountKey = (item: any): string => isBitcoin ? item.chain + item.address : item.evmChain + item.address;

    await awaitParallelExecution(
      accounts,
      getAccountKey,
      async item => syncTransactionTask(item, type),
      2,
    );

    if (!isBitcoin) {
      logger.debug(`queued ${chain} transactions for decoding`);
      queue.queue(chain, async () => {
        await decodeTransactionsTask(chain);
        logger.debug(`finished decoding ${chain} transactions`);
      });
    }
  };

  const { queryAllExchangeEvents, queryOnlineEvent } = useRefreshHandlers();

  const refreshTransactionsHandler = async (
    params: TransactionSyncParams,
  ): Promise<void> => {
    const { accounts, type } = params;
    logger.debug(`refreshing ${type} transactions for ${accounts.length} addresses`);

    const groupedByChains = Object.entries(
      groupBy(accounts, item => item.chain),
    ).map(([chain, data]) => ({
      chain,
      data,
    }));

    await awaitParallelExecution(
      groupedByChains,
      item => item.chain,
      async item => syncAndReDecodeEvents(item.chain, { accounts: item.data, type }),
      2,
    );

    if (accounts.length > 0)
      setStatus(isTaskRunning(TaskType.TX, { type }) ? Status.REFRESHING : Status.LOADED);
    logger.debug(`finished refreshing ${type} transactions for ${accounts.length} addresses`);
  };

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

  const refreshTransactions = async (params: RefreshTransactionsParams = {}): Promise<void> => {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    const { accounts, exchanges, queries } = payload;
    const fullRefresh = Object.keys(payload).length === 0;

    const { connectedExchanges } = storeToRefs(useSessionSettingsStore());

    // Get current accounts first to check if we have new ones
    let currentEvmAccounts: ChainAddress[] = [];
    let currentEvmLikeAccounts: ChainAddress[] = [];
    let currentBitcoinAccounts: ChainAddress[] = [];

    if (accounts && accounts.length > 0) {
      // Separate accounts by type
      accounts.forEach((account) => {
        if (isEvmLikeChains(account.chain)) {
          currentEvmLikeAccounts.push(account);
        }
        else if (isBtcChains(account.chain)) {
          currentBitcoinAccounts.push(account);
        }
        else {
          currentEvmAccounts.push(account);
        }
      });
    }
    else if (fullRefresh) {
      // Always get all accounts on full refresh to check for new ones
      currentEvmAccounts = getEvmAccounts(chains);
      currentEvmLikeAccounts = getEvmLikeAccounts(chains);
      currentBitcoinAccounts = getBitcoinAccounts(chains);
    }

    const allCurrentAccounts = [...currentEvmAccounts, ...currentEvmLikeAccounts, ...currentBitcoinAccounts];
    const newAccountsList = getNewAccounts(allCurrentAccounts);
    const hasNewAccounts = newAccountsList.length > 0;

    // Skip refresh only if fetchDisabled returns true AND there are no new accounts
    if (fetchDisabled(userInitiated) && !hasNewAccounts) {
      return;
    }

    // Use the already separated accounts
    let evmAccounts = currentEvmAccounts;
    let evmLikeAccounts = currentEvmLikeAccounts;
    let bitcoinAccounts = currentBitcoinAccounts;

    // Check if we need to refresh based on new accounts
    const allAccounts = allCurrentAccounts;
    // If refresh is already running, add new accounts to pending
    if (get(isRefreshing)) {
      const newAccounts = getNewAccounts(allAccounts);
      if (newAccounts.length > 0) {
        addPendingAccounts(newAccounts);
      }
      return;
    }

    // Check if we should refresh all accounts (includes new accounts check)
    if (fullRefresh && shouldRefreshAll(allAccounts)) {
      // Reset to refresh all accounts including new ones
      evmAccounts = getEvmAccounts(chains);
      evmLikeAccounts = getEvmLikeAccounts(chains);
      bitcoinAccounts = getBitcoinAccounts(chains);
    }
    else if (hasNewAccounts) {
      // If we have new accounts (either full or partial refresh), refresh only those
      evmAccounts = [];
      evmLikeAccounts = [];
      bitcoinAccounts = [];
      newAccountsList.forEach((account) => {
        if (isEvmLikeChains(account.chain)) {
          evmLikeAccounts.push(account);
        }
        else if (isBtcChains(account.chain)) {
          bitcoinAccounts.push(account);
        }
        else {
          evmAccounts.push(account);
        }
      });
    }

    const accountsToRefresh = [...evmAccounts, ...evmLikeAccounts, ...bitcoinAccounts];
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

      if (evmAccounts.length > 0) {
        asyncOperations.push(refreshTransactionsHandler({ accounts: evmAccounts, type: TransactionChainType.EVM }));
      }

      if (bitcoinAccounts.length > 0) {
        asyncOperations.push(refreshTransactionsHandler({ accounts: bitcoinAccounts, type: TransactionChainType.BITCOIN }));
      }

      if (evmLikeAccounts.length > 0) {
        asyncOperations.push(refreshTransactionsHandler({ accounts: evmLikeAccounts, type: TransactionChainType.EVMLIKE }));
      }

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

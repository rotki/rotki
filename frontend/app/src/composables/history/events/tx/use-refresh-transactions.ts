import type { Exchange } from '@/types/exchanges';
import type { RefreshTransactionsParams, TransactionSyncParams } from './types';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useModules } from '@/composables/session/modules';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
import { useStatusUpdater } from '@/composables/status';
import { useHistoryStore } from '@/store/history';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useNotificationsStore } from '@/store/notifications';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import {
  type BitcoinChainAddress,
  type BlockchainAddress,
  type EvmChainAddress,
  TransactionChainType,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { OnlineHistoryEventsQueryType } from '@/types/history/events/schemas';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { BackendCancelledTaskError, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';
import { groupBy, omit } from 'es-toolkit';

interface UseRefreshTransactionsReturn {
  refreshTransactions: (params?: RefreshTransactionsParams) => Promise<void>;
}

export function useRefreshTransactions(): UseRefreshTransactionsReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(1);
  const {
    fetchTransactionsTask,
    queryExchangeEvents,
    queryOnlineHistoryEvents,
  } = useHistoryEventsApi();

  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { initializeQueryStatus, removeQueryStatus } = useTxQueryStatusStore();
  const { getChain, getChainName, isEvmLikeChains } = useSupportedChains();
  const { getBitcoinAccounts, getEvmAccounts, getEvmLikeAccounts } = useHistoryTransactionAccounts();
  const { fetchDisabled, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY);
  const {
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
  } = useHistoryTransactionDecoding();
  const { resetUndecodedTransactionsStatus } = useHistoryStore();

  const getChainInfo = (
    account: EvmChainAddress | BitcoinChainAddress,
    type: TransactionChainType,
  ): { chainName: string; blockchain: string } => {
    if (type === TransactionChainType.BITCOIN && 'chain' in account) {
      const chainName = account.chain;
      return { blockchain: chainName, chainName };
    }
    else if ('evmChain' in account) {
      const chainName = account.evmChain;
      return { blockchain: getChain(chainName), chainName };
    }
    else {
      throw new Error('Invalid account type');
    }
  };

  const syncTransactionTask = async (
    account: EvmChainAddress | BitcoinChainAddress,
    type: TransactionChainType,
  ): Promise<void> => {
    const taskType = TaskType.TX;
    const address = account.address;
    const { blockchain, chainName } = getChainInfo(account, type);

    const blockchainAccount: BlockchainAddress = {
      address,
      blockchain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    const { taskId } = await fetchTransactionsTask(defaults);
    const taskMeta = {
      address,
      chain: chainName,
      description: t('actions.transactions.task.description', {
        address,
        chain: get(getChainName(blockchain)),
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
            chain: get(getChainName(blockchain)),
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
        await decodeTransactionsTask(chain, type);
        logger.debug(`finished decoding ${chain} transactions`);
      });
    }
  };

  const { isModuleEnabled } = useModules();
  const isEth2Enabled = isModuleEnabled(Module.ETH2);

  const { apiKey, credential } = useExternalApiKeys(t);

  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType): Promise<void> => {
    const eth2QueryTypes: OnlineHistoryEventsQueryType[] = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType))
      return;

    if (!get(apiKey('gnosis_pay')) && queryType === OnlineHistoryEventsQueryType.GNOSIS_PAY) {
      return;
    }

    if (!get(credential('monerium')) && queryType === OnlineHistoryEventsQueryType.MONERIUM) {
      return;
    }

    logger.debug(`querying for ${queryType} events`);
    const taskType = TaskType.QUERY_ONLINE_EVENTS;
    const { taskId } = await queryOnlineHistoryEvents({
      asyncQuery: true,
      queryType,
    });

    const taskMeta = {
      description: t('actions.online_events.task.description', {
        queryType,
      }),
      queryType,
      title: t('actions.online_events.task.title'),
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.online_events.error.description', {
            error,
            queryType,
          }),
          title: t('actions.online_events.error.title'),
        });
      }
    }
    logger.debug(`finished querying for ${queryType} events`);
  };

  const refreshTransactionsHandler = async (
    params: TransactionSyncParams,
  ): Promise<void> => {
    const { accounts, type } = params;
    logger.debug(`refreshing ${type} transactions for ${accounts.length} addresses`);
    const isBitcoin = type === TransactionChainType.BITCOIN;

    const getChainKey = (account: any): string => isBitcoin ? account.chain : account.evmChain;

    const groupedByChains = Object.entries(
      groupBy(accounts, getChainKey),
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

    if (!isBitcoin) {
      queue.queue(type, async () => fetchUndecodedTransactionsBreakdown(type));
    }

    if (accounts.length > 0)
      setStatus(isTaskRunning(TaskType.TX, { type }) ? Status.REFRESHING : Status.LOADED);
    logger.debug(`finished refreshing ${type} transactions for ${accounts.length} addresses`);
  };

  const queryExchange = async (payload: Exchange): Promise<void> => {
    logger.debug(`querying exchange events for ${payload.location} (${payload.name})`);
    const exchange = omit(payload, ['krakenAccountType']);
    const taskType = TaskType.QUERY_EXCHANGE_EVENTS;
    const taskMeta = {
      description: t('actions.exchange_events.task.description', exchange),
      exchange,
      title: t('actions.exchange_events.task.title'),
    };

    try {
      const { taskId } = await queryExchangeEvents(exchange);
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        logger.error(error);
        notify({
          display: true,
          message: t('actions.exchange_events.error.description', {
            error,
            ...exchange,
          }),
          title: t('actions.exchange_events.error.title'),
        });
      }
    }
  };

  const queryAllExchangeEvents = async (exchanges?: Exchange[]): Promise<void> => {
    const selectedExchanges = exchanges ?? get(connectedExchanges);
    const groupedExchanges = Object.entries(groupBy(selectedExchanges, exchange => exchange.location));

    await awaitParallelExecution(groupedExchanges, ([group]) => group, async ([_group, exchanges]) => {
      for (const exchange of exchanges) {
        await queryExchange(exchange);
      }
    }, 2);
  };

  const refreshTransactions = async (params: RefreshTransactionsParams = {}): Promise<void> => {
    const { chains = [], disableEvmEvents = false, payload = {}, userInitiated = false } = params;
    if (fetchDisabled(userInitiated)) {
      logger.info('skipping transaction refresh');
      return;
    }

    const { accounts, exchanges, queries } = payload;
    const fullRefresh = Object.keys(payload).length === 0;

    const evmAccounts: EvmChainAddress[] = [];
    const evmLikeAccounts: EvmChainAddress[] = [];
    const bitcoinAccounts: BitcoinChainAddress[] = [];

    if (accounts && accounts.length > 0) {
      // Separate accounts by type
      accounts.forEach((account) => {
        if ('evmChain' in account) {
          if (isEvmLikeChains(account.evmChain)) {
            evmLikeAccounts.push(account);
          }
          else {
            evmAccounts.push(account);
          }
        }
        else if ('chain' in account) {
          bitcoinAccounts.push(account);
        }
      });
    }
    else if (fullRefresh && !disableEvmEvents) {
      evmAccounts.push(...getEvmAccounts(chains));
      evmLikeAccounts.push(...getEvmLikeAccounts(chains));
      bitcoinAccounts.push(...getBitcoinAccounts(chains));
    }

    if (evmAccounts.length + evmLikeAccounts.length + bitcoinAccounts.length > 0) {
      setStatus(Status.REFRESHING);
      initializeQueryStatus(evmAccounts);
      resetUndecodedTransactionsStatus();
    }

    try {
      if (!disableEvmEvents && (fullRefresh || evmAccounts.length > 0))
        await fetchUndecodedTransactionsStatus();

      const asyncOperations: Promise<void>[] = [];

      if (fullRefresh || (accounts && accounts.length > 0)) {
        asyncOperations.push(refreshTransactionsHandler({ accounts: evmAccounts, type: TransactionChainType.EVM }));
      }

      if (fullRefresh || (accounts && bitcoinAccounts.length > 0)) {
        asyncOperations.push(refreshTransactionsHandler({ accounts: bitcoinAccounts, type: TransactionChainType.BITCOIN }));
      }

      if (fullRefresh) {
        asyncOperations.push(refreshTransactionsHandler({ accounts: evmLikeAccounts, type: TransactionChainType.EVMLIKE }));
      }

      if (fullRefresh || disableEvmEvents || exchanges) {
        asyncOperations.push(queryAllExchangeEvents(exchanges));
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

      if (!disableEvmEvents && evmAccounts.length > 0)
        queue.queue('undecoded-transactions-status-final', async () => fetchUndecodedTransactionsStatus());
    }
    catch (error) {
      logger.error(error);
      resetStatus();
    }
  };

  return {
    refreshTransactions,
  };
}

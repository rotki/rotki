import type { ActionStatus } from '@/types/action';
import type { Exchange } from '@/types/exchanges';
import type { RefreshTransactionsParams } from './types';
import { useHistoryEventsApi } from '@/composables/api/history/events';
import { useHistoryTransactionDecoding } from '@/composables/history/events/tx/decoding';
import { useHistoryTransactionAccounts } from '@/composables/history/events/tx/use-history-transaction-accounts';
import { useSupportedChains } from '@/composables/info/chains';
import { useModules } from '@/composables/session/modules';
import { useStatusUpdater } from '@/composables/status';
import { displayDateFormatter } from '@/data/date-formatter';
import { useHistoryStore } from '@/store/history';
import { useTxQueryStatusStore } from '@/store/history/query-status/tx-query-status';
import { useNotificationsStore } from '@/store/notifications';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { useSessionSettingsStore } from '@/store/settings/session';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import {
  type AddTransactionHashPayload,
  type BitcoinChainAddress,
  type BlockchainAddress,
  type EvmChainAddress,
  OnlineHistoryEventsQueryType,
  type RepullingTransactionPayload,
  type RepullingTransactionResponse,
  TransactionChainType,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { Module } from '@/types/modules';
import { Section, Status } from '@/types/status';
import { BackendCancelledTaskError, type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { awaitParallelExecution } from '@/utils/await-parallel-execution';
import { LimitedParallelizationQueue } from '@/utils/limited-parallelization-queue';
import { logger } from '@/utils/logging';
import { Severity, toHumanReadable } from '@rotki/common';
import { startPromise } from '@shared/utils';
import { groupBy, omit } from 'es-toolkit';

export const useHistoryTransactions = createSharedComposable(() => {
  const { t } = useI18n({ useScope: 'global' });
  const { notify } = useNotificationsStore();
  const queue = new LimitedParallelizationQueue(1);
  const {
    addTransactionHash: addTransactionHashCaller,
    fetchTransactionsTask,
    queryExchangeEvents,
    queryOnlineHistoryEvents,
    repullingTransactions: repullingTransactionsCaller,
  } = useHistoryEventsApi();

  const { connectedExchanges } = storeToRefs(useSessionSettingsStore());
  const { awaitTask, isTaskRunning } = useTaskStore();
  const { initializeQueryStatus, removeQueryStatus } = useTxQueryStatusStore();
  const { updateSetting } = useFrontendSettingsStore();
  const { getChain, isEvmLikeChains } = useSupportedChains();
  const { getBitcoinAccounts, getEvmAccounts, getEvmLikeAccounts } = useHistoryTransactionAccounts();
  const { fetchDisabled, getStatus, resetStatus, setStatus } = useStatusUpdater(Section.HISTORY);
  const {
    decodeTransactionsTask,
    fetchUndecodedTransactionsBreakdown,
    fetchUndecodedTransactionsStatus,
  } = useHistoryTransactionDecoding();
  const { resetProtocolCacheUpdatesStatus, resetUndecodedTransactionsStatus } = useHistoryStore();
  const { dateDisplayFormat } = storeToRefs(useGeneralSettingsStore());

  queue.setOnCompletion(() => {
    if (getStatus() === Status.LOADED) {
      logger.info('Enabling notifications for newly detected nfts');
      startPromise(updateSetting({ notifyNewNfts: true }));
      resetProtocolCacheUpdatesStatus();
    }
  });

  const syncTransactionTask = async (
    account: EvmChainAddress | BitcoinChainAddress,
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<void> => {
    const taskType = TaskType.TX;
    const isEvm = type === TransactionChainType.EVM;
    const isBitcoin = type === TransactionChainType.BITCOIN;

    const chainName = isBitcoin ? (account as BitcoinChainAddress).chain : (account as EvmChainAddress).evmChain;
    const blockchain = isBitcoin ? chainName : getChain(chainName);

    const blockchainAccount: BlockchainAddress = {
      address: account.address,
      blockchain,
    };
    const defaults: TransactionRequestPayload = {
      accounts: [blockchainAccount],
    };

    const { taskId } = await fetchTransactionsTask(defaults);
    const taskMeta = {
      address: account.address,
      chain: chainName,
      description: t('actions.transactions.task.description', blockchainAccount),
      isEvm,
      title: t('actions.transactions.task.title'),
    };

    try {
      await awaitTask<boolean, TaskMeta>(taskId, taskType, taskMeta, true);
    }
    catch (error: any) {
      if (error instanceof BackendCancelledTaskError) {
        logger.debug(error);
        if ('evmChain' in account) {
          removeQueryStatus(account);
        }
      }
      else if (!isTaskCancelled(error)) {
        notify({
          display: true,
          message: t('actions.transactions.error.description', {
            address: account.address,
            chain: toHumanReadable(chainName),
            error,
          }),
          title: t('actions.transactions.error.title'),
        });
      }
    }
    finally {
      setStatus(isTaskRunning(taskType, { isEvm }) ? Status.REFRESHING : Status.LOADED);
    }
  };

  const syncAndReDecodeEvents = async (
    chain: string,
    params: ({ accounts: EvmChainAddress[]; type: TransactionChainType.EVM | TransactionChainType.EVMLIKE } |
      { accounts: BitcoinChainAddress[]; type: TransactionChainType.BITCOIN }),
  ): Promise<void> => {
    const { accounts, type } = params;
    logger.debug(`syncing ${chain} transactions for ${accounts.length} addresses`);
    const isBitcoin = type === TransactionChainType.BITCOIN;

    if (isBitcoin) {
      await awaitParallelExecution(
        accounts,
        item => item.chain + item.address,
        async item => syncTransactionTask(item, type),
        2,
      );
    }
    else {
      await awaitParallelExecution(
        accounts,
        item => item.evmChain + item.address,
        async item => syncTransactionTask(item, type),
        2,
      );
    }

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

  const queryOnlineEvent = async (queryType: OnlineHistoryEventsQueryType): Promise<void> => {
    const eth2QueryTypes = [
      OnlineHistoryEventsQueryType.ETH_WITHDRAWALS,
      OnlineHistoryEventsQueryType.BLOCK_PRODUCTIONS,
    ];

    if (!get(isEth2Enabled) && eth2QueryTypes.includes(queryType))
      return;
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
    params: { addresses: EvmChainAddress[]; type: TransactionChainType.EVM | TransactionChainType.EVMLIKE } |
      { addresses: BitcoinChainAddress[]; type: TransactionChainType.BITCOIN },
  ): Promise<void> => {
    const { addresses, type } = params;
    logger.debug(`refreshing ${type} transactions for ${addresses.length} addresses`);
    const isBitcoin = type === TransactionChainType.BITCOIN;

    if (isBitcoin) {
      const groupedByChains = Object.entries(
        groupBy(addresses, account => (account).chain),
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
    }
    else {
      const groupedByChains = Object.entries(
        groupBy(addresses, account => (account).evmChain),
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
    }

    if (!isBitcoin) {
      queue.queue(type, async () => fetchUndecodedTransactionsBreakdown(type));
    }

    const isEvm = type === TransactionChainType.EVM;
    if (addresses.length > 0)
      setStatus(isTaskRunning(TaskType.TX, { isEvm }) ? Status.REFRESHING : Status.LOADED);
    logger.debug(`finished refreshing ${type} transactions for ${addresses.length} addresses`);
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
        asyncOperations.push(refreshTransactionsHandler({ addresses: evmAccounts, type: TransactionChainType.EVM }));
      }

      if (fullRefresh || (accounts && bitcoinAccounts.length > 0)) {
        asyncOperations.push(refreshTransactionsHandler({ addresses: bitcoinAccounts, type: TransactionChainType.BITCOIN }));
      }

      if (fullRefresh) {
        asyncOperations.push(refreshTransactionsHandler({ addresses: evmLikeAccounts, type: TransactionChainType.EVMLIKE }));
      }

      if (fullRefresh || disableEvmEvents || exchanges) {
        asyncOperations.push(queryAllExchangeEvents(exchanges));
      }

      const queriesToExecute: OnlineHistoryEventsQueryType[] | undefined = fullRefresh || disableEvmEvents
        ? Object.values(OnlineHistoryEventsQueryType) as unknown as OnlineHistoryEventsQueryType[]
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

  const addTransactionHash = async (
    payload: AddTransactionHashPayload,
  ): Promise<ActionStatus<ValidationErrors | string>> => {
    let success = false;
    let message: ValidationErrors | string = '';
    try {
      await addTransactionHashCaller(payload);
      success = true;
    }
    catch (error: any) {
      message = error.message;
      if (error instanceof ApiValidationError) {
        message = error.getValidationErrors(payload);
      }
    }

    return { message, success };
  };

  const repullingTransactions = async (payload: RepullingTransactionPayload, refresh: () => void): Promise<void> => {
    const taskType = TaskType.REPULLING_TXS;
    const { taskId } = await repullingTransactionsCaller(payload);

    const messagePayload = {
      address: payload.address,
      chain: payload.evmChain ? toHumanReadable(payload.evmChain) : undefined,
      from: displayDateFormatter.format(new Date(payload.fromTimestamp * 1000), get(dateDisplayFormat)),
      to: displayDateFormatter.format(new Date(payload.toTimestamp * 1000), get(dateDisplayFormat)),
    };

    const isAddressSpecified = payload.address && payload.evmChain;

    const taskMeta = {
      description: isAddressSpecified
        ? t('actions.repulling_transaction.task.description', messagePayload)
        : t('actions.repulling_transaction.task.no_address_or_chain_transaction', messagePayload),
      title: t('actions.repulling_transaction.task.title'),
    };

    const taskFunc = async (): Promise<void> => {
      try {
        const { result } = await awaitTask<RepullingTransactionResponse, TaskMeta>(taskId, taskType, taskMeta, true);
        const { newTransactionsCount } = result;
        notify({
          display: true,
          message: newTransactionsCount ? t('actions.repulling_transaction.success.description', { length: newTransactionsCount }) : t('actions.repulling_transaction.success.no_tx_description'),
          severity: Severity.INFO,
          title: t('actions.repulling_transaction.task.title'),
        });
        if (newTransactionsCount) {
          refresh();
        }
      }
      catch (error: any) {
        if (!isTaskCancelled(error)) {
          logger.error(error);
          notify({
            display: true,
            message: isAddressSpecified
              ? t('actions.repulling_transaction.error.description', messagePayload)
              : t('actions.repulling_transaction.error.no_address_or_chain_transaction', messagePayload),
            title: t('actions.repulling_transaction.task.title'),
          });
        }
      }
    };

    startPromise(taskFunc());
  };

  return {
    addTransactionHash,
    refreshTransactions,
    repullingTransactions,
  };
});

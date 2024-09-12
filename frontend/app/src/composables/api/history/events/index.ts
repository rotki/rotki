import { omit } from 'lodash-es';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validTaskStatus,
  validWithParamsSessionAndExternalService,
} from '@/services/utils';
import {
  type AddTransactionHashPayload,
  type ChainAndTxHash,
  type EditHistoryEventPayload,
  type EvmChainAndTxHash,
  HistoryEventDetail,
  type HistoryEventEntryWithMeta,
  type HistoryEventRequestPayload,
  HistoryEventsCollectionResponse,
  type NewHistoryEventPayload,
  type OnlineHistoryEventsRequestPayload,
  TransactionChainType,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { type HistoryEventProductData, HistoryEventTypeData } from '@/types/history/events/event-type';
import type { CollectionResponse } from '@/types/collection';
import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';
import type { ActionDataEntry } from '@/types/action';

interface UseHistoryEventsApiReturn {
  fetchTransactionsTask: (payload: TransactionRequestPayload, type?: TransactionChainType) => Promise<PendingTask>;
  deleteTransactions: (chain: string, txHash?: string) => Promise<boolean>;
  pullAndRecodeTransactionRequest: (payload: ChainAndTxHash | EvmChainAndTxHash, type?: TransactionChainType) => Promise<PendingTask>;
  getUndecodedTransactionsBreakdown: (type?: TransactionChainType) => Promise<PendingTask>;
  decodeTransactions: (chains: string[], type?: TransactionChainType, ignoreCache?: boolean) => Promise<PendingTask>;
  addHistoryEvent: (event: NewHistoryEventPayload) => Promise<{ identifier: number }>;
  editHistoryEvent: (event: EditHistoryEventPayload) => Promise<boolean>;
  deleteHistoryEvent: (identifiers: number[], forceDelete?: boolean) => Promise<boolean>;
  getEventDetails: (identifier: number) => Promise<HistoryEventDetail>;
  addTransactionHash: (payload: AddTransactionHashPayload) => Promise<boolean>;
  getTransactionTypeMappings: () => Promise<HistoryEventTypeData>;
  getHistoryEventCounterpartiesData: () => Promise<ActionDataEntry[]>;
  getHistoryEventProductsData: () => Promise<HistoryEventProductData>;
  fetchHistoryEvents: (payload: HistoryEventRequestPayload) => Promise<CollectionResponse<HistoryEventEntryWithMeta>>;
  queryOnlineHistoryEvents: (payload: OnlineHistoryEventsRequestPayload) => Promise<PendingTask>;
  exportHistoryEventsCSV: (filters: HistoryEventRequestPayload, directoryPath?: string) => Promise<PendingTask>;
}

export function useHistoryEventsApi(): UseHistoryEventsApiReturn {
  const internalTransactions = async <T>(
    payload: TransactionRequestPayload,
    asyncQuery: boolean,
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<T> => {
    const accounts
      = type === TransactionChainType.EVM
        ? payload.accounts
        : payload.accounts.map(({ address, evmChain }) => ({ address, chain: evmChain }));
    const response = await api.instance.post<ActionResult<T>>(
      `/blockchains/${type}/transactions`,
      snakeCaseTransformer(
        nonEmptyProperties({
          asyncQuery,
          accounts,
        }),
      ),
      {
        paramsSerializer,
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const fetchTransactionsTask = (
    payload: TransactionRequestPayload,
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<PendingTask> => internalTransactions<PendingTask>(payload, true, type);

  const deleteTransactions = async (chain: string, txHash?: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/blockchains/transactions', {
      validateStatus: validStatus,
      data: chain ? snakeCaseTransformer({ chain, txHash }) : null,
    });

    return handleResponse(response);
  };

  const pullAndRecodeTransactionRequest = async (
    payload: ChainAndTxHash | EvmChainAndTxHash,
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      `blockchains/${type}/transactions`,
      snakeCaseTransformer({
        asyncQuery: true,
        ...payload,
      }),
    );

    return handleResponse(response);
  };

  const getUndecodedTransactionsBreakdown = async (
    type: TransactionChainType = TransactionChainType.EVM,
  ): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(`/blockchains/${type}/transactions/decode`, {
      params: snakeCaseTransformer({
        asyncQuery: true,
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const decodeTransactions = async (
    chains: string[],
    type: TransactionChainType = TransactionChainType.EVM,
    ignoreCache = false,
  ): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      `/blockchains/${type}/transactions/decode`,
      snakeCaseTransformer({
        asyncQuery: true,
        chains,
        ...(ignoreCache ? { ignoreCache } : {}),
      }),
      { validateStatus: validStatus },
    );

    return handleResponse(response);
  };

  const addHistoryEvent = async (event: NewHistoryEventPayload): Promise<{ identifier: number }> => {
    const response = await api.instance.put<ActionResult<{ identifier: number }>>(
      '/history/events',
      snakeCaseTransformer(event),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const editHistoryEvent = async (event: EditHistoryEventPayload): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>('/history/events', snakeCaseTransformer(event), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const deleteHistoryEvent = async (identifiers: number[], forceDelete = false): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/history/events', {
      data: snakeCaseTransformer({ identifiers, forceDelete }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const getEventDetails = async (identifier: number): Promise<HistoryEventDetail> => {
    const response = await api.instance.get<ActionResult<HistoryEventDetail>>('/history/events/details', {
      params: snakeCaseTransformer({ identifier }),
    });
    return HistoryEventDetail.parse(handleResponse(response));
  };

  const addTransactionHash = async (payload: AddTransactionHashPayload): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/blockchains/evm/transactions/add-hash',
      snakeCaseTransformer(payload),
      {
        validateStatus: validTaskStatus,
      },
    );

    return handleResponse(response);
  };

  const getTransactionTypeMappings = async (): Promise<HistoryEventTypeData> => {
    const response = await api.instance.get<ActionResult<HistoryEventTypeData>>('/history/events/type_mappings', {
      validateStatus: validStatus,
    });

    return HistoryEventTypeData.parse(handleResponse(response));
  };

  const getHistoryEventCounterpartiesData = async (): Promise<ActionDataEntry[]> => {
    const response = await api.instance.get<ActionResult<ActionDataEntry[]>>('/history/events/counterparties', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const getHistoryEventProductsData = async (): Promise<HistoryEventProductData> => {
    const response = await api.instance.get<ActionResult<HistoryEventProductData>>('/history/events/products', {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const fetchHistoryEvents = async (
    payload: HistoryEventRequestPayload,
  ): Promise<CollectionResponse<HistoryEventEntryWithMeta>> => {
    const response = await api.instance.post<ActionResult<CollectionResponse<HistoryEventEntryWithMeta>>>(
      '/history/events',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return HistoryEventsCollectionResponse.parse(handleResponse(response));
  };

  const queryOnlineHistoryEvents = async (payload: OnlineHistoryEventsRequestPayload): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/history/events/query',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const exportHistoryEventsCSV = async (
    filters: HistoryEventRequestPayload,
    directoryPath?: string,
  ): Promise<PendingTask> => {
    const func = directoryPath
      ? api.instance.post<ActionResult<PendingTask>>
      : api.instance.put<ActionResult<PendingTask>>;
    const response = await func(
      '/history/events/export',
      snakeCaseTransformer({
        directoryPath,
        asyncQuery: true,
        ...omit(filters, ['accounts']),
      }),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    fetchTransactionsTask,
    deleteTransactions,
    pullAndRecodeTransactionRequest,
    getUndecodedTransactionsBreakdown,
    decodeTransactions,
    addHistoryEvent,
    editHistoryEvent,
    deleteHistoryEvent,
    getEventDetails,
    addTransactionHash,
    getTransactionTypeMappings,
    getHistoryEventCounterpartiesData,
    getHistoryEventProductsData,
    fetchHistoryEvents,
    queryOnlineHistoryEvents,
    exportHistoryEventsCSV,
  };
}

import type { HistoryEventExportPayload, HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { ActionDataEntry, ActionStatus } from '@/types/action';
import type { CollectionResponse } from '@/types/collection';
import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';
import type { AxiosRequestConfig } from 'axios';
import { snakeCaseTransformer } from '@/services/axios-transformers';
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
  HistoryEventDetail,
  type PullEthBlockEventPayload,
  type PullTransactionPayload,
  type RepullingTransactionPayload,
  TransactionChainType,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { type HistoryEventProductData, HistoryEventTypeData } from '@/types/history/events/event-type';
import {
  type AddHistoryEventPayload,
  type HistoryEventCollectionRow,
  HistoryEventsCollectionResponse,
  type ModifyHistoryEventPayload,
  type OnlineHistoryEventsRequestPayload,
} from '@/types/history/events/schemas';
import { nonEmptyProperties } from '@/utils/data';
import { downloadFileByUrl } from '@/utils/download';
import { getFilename } from '@/utils/file';
import { omit } from 'es-toolkit';

interface QueryExchangePayload { name: string; location: string }

interface EvmTransactionStatus {
  lastQueriedTs: number;
  pendingDecode: boolean;
}

interface UseHistoryEventsApiReturn {
  fetchTransactionsTask: (payload: TransactionRequestPayload) => Promise<PendingTask>;
  deleteTransactions: (chain: string, txHash?: string) => Promise<boolean>;
  pullAndRecodeTransactionRequest: (payload: PullTransactionPayload, type?: TransactionChainType) => Promise<PendingTask>;
  getUndecodedTransactionsBreakdown: (type?: TransactionChainType) => Promise<PendingTask>;
  decodeTransactions: (chains: string[], type?: TransactionChainType, ignoreCache?: boolean) => Promise<PendingTask>;
  addHistoryEvent: (event: AddHistoryEventPayload) => Promise<{ identifier: number }>;
  editHistoryEvent: (event: ModifyHistoryEventPayload) => Promise<boolean>;
  deleteHistoryEvent: (identifiers: number[], forceDelete?: boolean) => Promise<boolean>;
  getEventDetails: (identifier: number) => Promise<HistoryEventDetail>;
  addTransactionHash: (payload: AddTransactionHashPayload) => Promise<boolean>;
  repullingTransactions: (payload: RepullingTransactionPayload) => Promise<PendingTask>;
  getTransactionTypeMappings: () => Promise<HistoryEventTypeData>;
  getHistoryEventCounterpartiesData: () => Promise<ActionDataEntry[]>;
  getHistoryEventProductsData: () => Promise<HistoryEventProductData>;
  fetchHistoryEvents: (payload: HistoryEventRequestPayload) => Promise<CollectionResponse<HistoryEventCollectionRow>>;
  queryOnlineHistoryEvents: (payload: OnlineHistoryEventsRequestPayload) => Promise<PendingTask>;
  queryExchangeEvents: (payload: QueryExchangePayload) => Promise<PendingTask>;
  exportHistoryEventsCSV: (filters: HistoryEventExportPayload, directoryPath?: string) => Promise<PendingTask>;
  downloadHistoryEventsCSV: (filePath: string) => Promise<ActionStatus>;
  deleteStakeEvents: (entryType: string) => Promise<boolean>;
  pullAndRecodeEthBlockEventRequest: (payload: PullEthBlockEventPayload) => Promise<PendingTask>;
  getEvmTransactionStatus: () => Promise<EvmTransactionStatus>;
}

export function useHistoryEventsApi(): UseHistoryEventsApiReturn {
  const internalTransactions = async <T>(
    payload: TransactionRequestPayload,
    asyncQuery: boolean,
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/blockchains/transactions',
      snakeCaseTransformer(
        nonEmptyProperties({
          accounts: payload.accounts,
          asyncQuery,
        }),
      ),
      {
        paramsSerializer,
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  const fetchTransactionsTask = async (
    payload: TransactionRequestPayload,
  ): Promise<PendingTask> => internalTransactions<PendingTask>(payload, true);

  const deleteTransactions = async (chain: string, txHash?: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/blockchains/transactions', {
      data: chain ? snakeCaseTransformer({ chain, txHash }) : null,
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const pullAndRecodeTransactionRequest = async (
    payload: PullTransactionPayload,
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

  const addHistoryEvent = async (event: AddHistoryEventPayload): Promise<{ identifier: number }> => {
    const response = await api.instance.put<ActionResult<{ identifier: number }>>(
      '/history/events',
      snakeCaseTransformer(event),
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  const editHistoryEvent = async (event: ModifyHistoryEventPayload): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>('/history/events', snakeCaseTransformer(event), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const deleteHistoryEvent = async (identifiers: number[], forceDelete = false): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/history/events', {
      data: snakeCaseTransformer({ forceDelete, identifiers }),
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

  const repullingTransactions = async (payload: RepullingTransactionPayload): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/blockchains/evm/transactions/refetch',
      snakeCaseTransformer({
        ...payload,
        asyncQuery: true,
      }),
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
  ): Promise<CollectionResponse<HistoryEventCollectionRow>> => {
    const response = await api.instance.post<ActionResult<CollectionResponse<HistoryEventCollectionRow>>>(
      '/history/events',
      snakeCaseTransformer(payload),
      {
        timeout: 90_000,
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

  const queryExchangeEvents = async (payload: QueryExchangePayload): Promise<PendingTask> => {
    const response = await api.instance.post(
      '/history/events/query/exchange',
      snakeCaseTransformer({
        ...payload,
        asyncQuery: true,
      }),
      {
        validateStatus: validStatus,
      },
    );
    return handleResponse(response);
  };

  const exportHistoryEventsCSV = async (
    filters: HistoryEventExportPayload & { accounts?: [] },
    directoryPath?: string,
  ): Promise<PendingTask> => {
    const requestBody = snakeCaseTransformer({
      asyncQuery: true,
      directoryPath,
      ...omit(filters, ['accounts']),
    });
    const url = '/history/events/export';
    const config: AxiosRequestConfig<typeof requestBody> = {
      validateStatus: validStatus,
    };
    const response = directoryPath
      ? await api.instance.post<ActionResult<PendingTask>>(url, requestBody, config)
      : await api.instance.put<ActionResult<PendingTask>>(url, requestBody, config);

    return handleResponse(response);
  };

  const downloadHistoryEventsCSV = async (filePath: string): Promise<ActionStatus> => {
    try {
      const fullUrl = api.instance.getUri({ params: snakeCaseTransformer({ filePath }), url: '/history/events/export/download' });

      downloadFileByUrl(fullUrl, getFilename(filePath));
      return { success: true };
    }
    catch (error: any) {
      return { message: error.message, success: false };
    }
  };

  const deleteStakeEvents = async (entryType: string): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/blockchains/eth2/stake/events', {
      data: snakeCaseTransformer({ entryType }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const pullAndRecodeEthBlockEventRequest = async (
    payload: PullEthBlockEventPayload,
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/blockchains/eth2/stake/events',
      snakeCaseTransformer({
        asyncQuery: true,
        ...payload,
      }),
    );

    return handleResponse(response);
  };

  const getEvmTransactionStatus = async (): Promise<EvmTransactionStatus> => {
    const response = await api.instance.get<ActionResult<any>>(
      '/blockchains/evm/transactions/status',
      {
        validateStatus: validStatus,
      },
    );

    return handleResponse(response);
  };

  return {
    addHistoryEvent,
    addTransactionHash,
    decodeTransactions,
    deleteHistoryEvent,
    deleteStakeEvents,
    deleteTransactions,
    downloadHistoryEventsCSV,
    editHistoryEvent,
    exportHistoryEventsCSV,
    fetchHistoryEvents,
    fetchTransactionsTask,
    getEventDetails,
    getEvmTransactionStatus,
    getHistoryEventCounterpartiesData,
    getHistoryEventProductsData,
    getTransactionTypeMappings,
    getUndecodedTransactionsBreakdown,
    pullAndRecodeEthBlockEventRequest,
    pullAndRecodeTransactionRequest,
    queryExchangeEvents,
    queryOnlineHistoryEvents,
    repullingTransactions,
  };
}

import type { HistoryEventExportPayload, HistoryEventRequestPayload } from '@/modules/history/events/request-types';
import type { CollectionResponse } from '@/types/collection';
import type { QueryExchangeEventsPayload } from '@/types/exchanges';
import { omit } from 'es-toolkit';
import { z } from 'zod/v4';
import { api } from '@/modules/api/rotki-api';
import { VALID_TASK_STATUS, VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type ActionDataEntry, ActionDataEntryArraySchema, type ActionStatus } from '@/types/action';
import {
  type AddTransactionHashPayload,
  HistoryEventDetail,
  type PullEthBlockEventPayload,
  type PullTransactionPayload,
  type RepullingExchangeEventsPayload,
  type RepullingTransactionPayload,
  type TransactionRequestPayload,
} from '@/types/history/events';
import { HistoryEventTypeData } from '@/types/history/events/event-type';
import {
  type AddHistoryEventPayload,
  type HistoryEventCollectionRow,
  HistoryEventsCollectionResponse,
  type ModifyHistoryEventPayload,
  type OnlineHistoryEventsRequestPayload,
} from '@/types/history/events/schemas';
import { type PendingTask, PendingTaskSchema } from '@/types/task';
import { downloadFileByUrl } from '@/utils/download';
import { getFilename } from '@/utils/file';

const TransactionStatusSchema = z.object({
  evmLastQueriedTs: z.number(),
  exchangesLastQueriedTs: z.number(),
  hasEvmAccounts: z.boolean(),
  hasExchangesAccounts: z.boolean(),
  undecodedTxCount: z.number(),
});

export type TransactionStatus = z.infer<typeof TransactionStatusSchema>;

interface UseHistoryEventsApiReturn {
  fetchTransactionsTask: (payload: TransactionRequestPayload) => Promise<PendingTask>;
  deleteTransactions: (chain: string, txRef?: string) => Promise<boolean>;
  pullAndRecodeTransactionRequest: (payload: PullTransactionPayload) => Promise<PendingTask>;
  getUndecodedTransactionsBreakdown: () => Promise<PendingTask>;
  decodeTransactions: (chains: string, ignoreCache?: boolean) => Promise<PendingTask>;
  addHistoryEvent: (event: AddHistoryEventPayload) => Promise<{ identifier: number }>;
  editHistoryEvent: (event: ModifyHistoryEventPayload) => Promise<boolean>;
  deleteHistoryEvent: (identifiers: number[], forceDelete?: boolean) => Promise<boolean>;
  getEventDetails: (identifier: number) => Promise<HistoryEventDetail>;
  addTransactionHash: (payload: AddTransactionHashPayload) => Promise<boolean>;
  repullingTransactions: (payload: RepullingTransactionPayload) => Promise<PendingTask>;
  repullingExchangeEvents: (payload: RepullingExchangeEventsPayload) => Promise<PendingTask>;
  getTransactionTypeMappings: () => Promise<HistoryEventTypeData>;
  getHistoryEventCounterpartiesData: () => Promise<ActionDataEntry[]>;
  fetchHistoryEvents: (payload: HistoryEventRequestPayload) => Promise<CollectionResponse<HistoryEventCollectionRow>>;
  queryOnlineHistoryEvents: (payload: OnlineHistoryEventsRequestPayload) => Promise<PendingTask>;
  queryExchangeEvents: (payload: QueryExchangeEventsPayload) => Promise<PendingTask>;
  exportHistoryEventsCSV: (filters: HistoryEventExportPayload, directoryPath?: string) => Promise<PendingTask>;
  downloadHistoryEventsCSV: (filePath: string) => Promise<ActionStatus>;
  deleteStakeEvents: (entryType: string) => Promise<boolean>;
  pullAndRecodeEthBlockEventRequest: (payload: PullEthBlockEventPayload) => Promise<PendingTask>;
  getTransactionStatusSummary: () => Promise<TransactionStatus>;
}

export function useHistoryEventsApi(): UseHistoryEventsApiReturn {
  const internalTransactions = async <T>(
    payload: TransactionRequestPayload,
    asyncQuery: boolean,
  ): Promise<T> => api.post<T>(
    '/blockchains/transactions',
    {
      accounts: payload.accounts,
      asyncQuery,
    },
    {
      filterEmptyProperties: true,
      validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
    },
  );

  const fetchTransactionsTask = async (
    payload: TransactionRequestPayload,
  ): Promise<PendingTask> => {
    const response = await internalTransactions<PendingTask>(payload, true);
    return PendingTaskSchema.parse(response);
  };

  const deleteTransactions = async (chain: string, txRef?: string): Promise<boolean> => api.delete<boolean>('/blockchains/transactions', {
    body: chain ? { chain, txRef } : null,
  });

  const pullAndRecodeTransactionRequest = async (
    payload: PullTransactionPayload,
  ): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      `/blockchains/transactions/decode`,
      {
        asyncQuery: true,
        ...payload,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const getUndecodedTransactionsBreakdown = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>(`/blockchains/transactions/decode`, {
      query: { asyncQuery: true },
    });

    return PendingTaskSchema.parse(response);
  };

  const decodeTransactions = async (
    chain: string,
    ignoreCache = false,
  ): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      `/blockchains/transactions/decode`,
      {
        asyncQuery: true,
        chain,
        ...(ignoreCache ? { ignoreCache } : {}),
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const addHistoryEvent = async (event: AddHistoryEventPayload): Promise<{ identifier: number }> => api.put<{ identifier: number }>(
    '/history/events',
    event,
  );

  const editHistoryEvent = async (event: ModifyHistoryEventPayload): Promise<boolean> => api.patch<boolean>('/history/events', event);

  const deleteHistoryEvent = async (identifiers: number[], forceDelete = false): Promise<boolean> => api.delete<boolean>('/history/events', {
    body: { forceDelete, identifiers },
  });

  const getEventDetails = async (identifier: number): Promise<HistoryEventDetail> => {
    const response = await api.get<HistoryEventDetail>('/history/events/details', {
      query: { identifier },
    });
    return HistoryEventDetail.parse(response);
  };

  const addTransactionHash = async (payload: AddTransactionHashPayload): Promise<boolean> => api.put<boolean>(
    '/blockchains/transactions',
    payload,
    {
      validStatuses: VALID_TASK_STATUS,
    },
  );

  const repullingTransactions = async (payload: RepullingTransactionPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/blockchains/transactions/refetch',
      {
        ...payload,
        asyncQuery: true,
      },
      {
        validStatuses: VALID_TASK_STATUS,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const repullingExchangeEvents = async (payload: RepullingExchangeEventsPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/history/events/query/exchange/range',
      {
        ...payload,
        asyncQuery: true,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const getTransactionTypeMappings = async (): Promise<HistoryEventTypeData> => {
    const response = await api.get<HistoryEventTypeData>('/history/events/type_mappings');

    return HistoryEventTypeData.parse(response);
  };

  const getHistoryEventCounterpartiesData = async (): Promise<ActionDataEntry[]> => {
    const response = await api.get<ActionDataEntry[]>('/history/events/counterparties');
    return ActionDataEntryArraySchema.parse(response) as ActionDataEntry[];
  };

  const fetchHistoryEvents = async (
    payload: HistoryEventRequestPayload,
  ): Promise<CollectionResponse<HistoryEventCollectionRow>> => {
    const response = await api.post<CollectionResponse<HistoryEventCollectionRow>>(
      '/history/events',
      payload,
      {
        timeout: 90_000,
      },
    );

    return HistoryEventsCollectionResponse.parse(response);
  };

  const queryOnlineHistoryEvents = async (payload: OnlineHistoryEventsRequestPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/history/events/query',
      payload,
    );

    return PendingTaskSchema.parse(response);
  };

  const queryExchangeEvents = async (payload: QueryExchangeEventsPayload): Promise<PendingTask> => {
    const response = await api.post<PendingTask>(
      '/history/events/query/exchange',
      {
        ...payload,
        asyncQuery: true,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const exportHistoryEventsCSV = async (
    filters: HistoryEventExportPayload & { accounts?: [] },
    directoryPath?: string,
  ): Promise<PendingTask> => {
    const requestBody = {
      asyncQuery: true,
      directoryPath,
      ...omit(filters, ['accounts']),
    };
    const url = '/history/events/export';

    const response = directoryPath
      ? await api.post<PendingTask>(url, requestBody)
      : await api.put<PendingTask>(url, requestBody);

    return PendingTaskSchema.parse(response);
  };

  const downloadHistoryEventsCSV = async (filePath: string): Promise<ActionStatus> => {
    try {
      const fullUrl = api.buildUrl('/history/events/export/download', { filePath });
      downloadFileByUrl(fullUrl, getFilename(filePath));
      return { success: true };
    }
    catch (error: any) {
      return { message: error.message, success: false };
    }
  };

  const deleteStakeEvents = async (entryType: string): Promise<boolean> => api.delete<boolean>('/blockchains/eth2/stake/events', {
    body: { entryType },
  });

  const pullAndRecodeEthBlockEventRequest = async (
    payload: PullEthBlockEventPayload,
  ): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/blockchains/eth2/stake/events',
      {
        asyncQuery: true,
        ...payload,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  const getTransactionStatusSummary = async (): Promise<TransactionStatus> => {
    const response = await api.get<TransactionStatus>('/history/status/summary');

    return TransactionStatusSchema.parse(response);
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
    getHistoryEventCounterpartiesData,
    getTransactionStatusSummary,
    getTransactionTypeMappings,
    getUndecodedTransactionsBreakdown,
    pullAndRecodeEthBlockEventRequest,
    pullAndRecodeTransactionRequest,
    queryExchangeEvents,
    queryOnlineHistoryEvents,
    repullingExchangeEvents,
    repullingTransactions,
  };
}

import { type ActionResult } from '@rotki/common/lib/data';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validTaskStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import { transformCase } from '@/utils/text';
import { type CollectionResponse } from '@/types/collection';
import {
  type AddTransactionHashPayload,
  type AddressesAndEvmChainPayload,
  type EditEvmHistoryEventPayload,
  HistoryEventDetail,
  type HistoryEventEntryWithMeta,
  type HistoryEventRequestPayload,
  HistoryEventsCollectionResponse,
  type NewEvmHistoryEventPayload,
  type OnlineHistoryEventsRequestPayload,
  type TransactionEventRequestPayload,
  type TransactionRequestPayload
} from '@/types/history/events';
import { type PendingTask } from '@/types/task';
import {
  type HistoryEventProductData,
  HistoryEventTypeData
} from '@/types/history/events/event-type';
import { type ActionDataEntry } from '@/types/action';

export const useHistoryEventsApi = () => {
  const internalEvmTransactions = async <T>(
    payload: TransactionRequestPayload,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      `/blockchains/evm/transactions`,
      snakeCaseTransformer(
        nonEmptyProperties({
          asyncQuery,
          ...payload,
          orderByAttributes:
            payload.orderByAttributes?.map(item => transformCase(item)) ?? []
        })
      ),
      {
        paramsSerializer,
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  const fetchEvmTransactionsTask = async (
    payload: TransactionRequestPayload
  ): Promise<PendingTask> =>
    internalEvmTransactions<PendingTask>(payload, true);

  const deleteEvmTransactions = async (): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      `/blockchains/evm/transactions`,
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const decodeHistoryEvents = async (
    payload: TransactionEventRequestPayload
  ): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      'blockchains/evm/transactions',
      snakeCaseTransformer({
        asyncQuery: true,
        ...payload
      })
    );

    return handleResponse(response);
  };

  const reDecodeMissingTransactionEvents = async <T>(
    data: AddressesAndEvmChainPayload[],
    asyncQuery = true
  ): Promise<T> => {
    const response = await api.instance.post<ActionResult<T>>(
      '/blockchains/evm/transactions/decode',
      snakeCaseTransformer({
        asyncQuery,
        data
      }),
      { validateStatus: validStatus }
    );

    return handleResponse(response);
  };

  const addTransactionEvent = async (
    event: NewEvmHistoryEventPayload
  ): Promise<{ identifier: number }> => {
    const response = await api.instance.put<
      ActionResult<{ identifier: number }>
    >('/history/events', snakeCaseTransformer(event), {
      validateStatus: validStatus
    });

    return handleResponse(response);
  };

  const editTransactionEvent = async (
    event: EditEvmHistoryEventPayload
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/history/events',
      snakeCaseTransformer(event),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteTransactionEvent = async (
    identifiers: number[],
    forceDelete = false
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/history/events',
      {
        data: snakeCaseTransformer({ identifiers, forceDelete }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const getEventDetails = async (
    identifier: number
  ): Promise<HistoryEventDetail> => {
    const response = await api.instance.get<ActionResult<HistoryEventDetail>>(
      '/history/events/details',
      {
        params: snakeCaseTransformer({ identifier })
      }
    );
    return HistoryEventDetail.parse(handleResponse(response));
  };

  const addTransactionHash = async (
    payload: AddTransactionHashPayload
  ): Promise<boolean> => {
    const response = await api.instance.put<ActionResult<boolean>>(
      '/blockchains/evm/transactions/add-hash',
      snakeCaseTransformer(payload),
      {
        validateStatus: validTaskStatus
      }
    );

    return handleResponse(response);
  };

  const getTransactionTypeMappings =
    async (): Promise<HistoryEventTypeData> => {
      const response = await api.instance.get<
        ActionResult<HistoryEventTypeData>
      >('/history/events/type_mappings', {
        validateStatus: validStatus
      });

      return HistoryEventTypeData.parse(handleResponse(response));
    };

  const getHistoryEventCounterpartiesData = async (): Promise<
    ActionDataEntry[]
  > => {
    const response = await api.instance.get<ActionResult<ActionDataEntry[]>>(
      '/history/events/counterparties',
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const getHistoryEventProductsData =
    async (): Promise<HistoryEventProductData> => {
      const response = await api.instance.get<
        ActionResult<HistoryEventProductData>
      >('/history/events/products', {
        validateStatus: validStatus
      });

      return handleResponse(response);
    };

  const fetchHistoryEvents = async (
    payload: HistoryEventRequestPayload
  ): Promise<CollectionResponse<HistoryEventEntryWithMeta>> => {
    const response = await api.instance.post<
      ActionResult<CollectionResponse<HistoryEventEntryWithMeta>>
    >('/history/events', snakeCaseTransformer(payload), {
      validateStatus: validStatus
    });

    return HistoryEventsCollectionResponse.parse(handleResponse(response));
  };

  const queryOnlineHistoryEvents = async (
    payload: OnlineHistoryEventsRequestPayload
  ): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/history/events/query',
      snakeCaseTransformer(payload),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    fetchEvmTransactionsTask,
    deleteEvmTransactions,
    decodeHistoryEvents,
    reDecodeMissingTransactionEvents,
    addTransactionEvent,
    editTransactionEvent,
    deleteTransactionEvent,
    getEventDetails,
    addTransactionHash,
    getTransactionTypeMappings,
    getHistoryEventCounterpartiesData,
    getHistoryEventProductsData,
    fetchHistoryEvents,
    queryOnlineHistoryEvents
  };
};

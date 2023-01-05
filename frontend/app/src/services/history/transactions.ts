import { type ActionResult } from '@rotki/common/lib/data';
import {
  axiosSnakeCaseTransformer,
  getUpdatedKey
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { type PendingTask } from '@/services/types-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import { type CollectionResponse } from '@/types/collection';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type AddressesAndEvmChainPayload,
  type EthTransaction,
  EthTransactionCollectionResponse,
  type NewEthTransactionEvent,
  type TransactionEventRequestPayload,
  type TransactionRequestPayload
} from '@/types/history/tx';

export const useTransactionsApi = () => {
  const internalEthTransactions = async <T>(
    payload: TransactionRequestPayload,
    asyncQuery: boolean
  ): Promise<T> => {
    let url = `/blockchains/evm/transactions`;
    const { address, ...data } = payload;
    if (address) {
      url += `/${address}`;
    }
    const response = await api.instance.get<ActionResult<T>>(url, {
      params: axiosSnakeCaseTransformer({
        asyncQuery,
        ...data,
        orderByAttributes:
          payload.orderByAttributes?.map(item => getUpdatedKey(item, false)) ??
          []
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService
    });

    return handleResponse(response);
  };

  const fetchEthTransactionsTask = async (
    payload: TransactionRequestPayload
  ): Promise<PendingTask> => {
    return internalEthTransactions<PendingTask>(payload, true);
  };

  const fetchEthTransactions = async (
    payload: TransactionRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<EthTransaction>>> => {
    const response = await internalEthTransactions<
      CollectionResponse<EntryWithMeta<EthTransaction>>
    >(payload, false);

    return EthTransactionCollectionResponse.parse(response);
  };

  const deleteEthTransactions = async (): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      `/blockchains/evm/transactions`,
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const fetchEthTransactionEvents = async (
    payload: TransactionEventRequestPayload
  ): Promise<PendingTask> => {
    const response = await api.instance.post<ActionResult<PendingTask>>(
      'blockchains/evm/transactions',
      axiosSnakeCaseTransformer({
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
      axiosSnakeCaseTransformer({
        asyncQuery,
        data
      }),
      { validateStatus: validStatus }
    );

    return handleResponse(response);
  };

  const addTransactionEvent = async (
    event: NewEthTransactionEvent
  ): Promise<{ identifier: number }> => {
    const response = await api.instance.put<
      ActionResult<{ identifier: number }>
    >('/history/events', axiosSnakeCaseTransformer(event), {
      validateStatus: validStatus
    });

    return handleResponse(response);
  };

  const editTransactionEvent = async (
    event: NewEthTransactionEvent
  ): Promise<boolean> => {
    const response = await api.instance.patch<ActionResult<boolean>>(
      '/history/events',
      axiosSnakeCaseTransformer(event),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteTransactionEvent = async (
    identifiers: number[]
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/history/events',
      {
        data: axiosSnakeCaseTransformer({ identifiers }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    fetchEthTransactionsTask,
    fetchEthTransactions,
    deleteEthTransactions,
    fetchEthTransactionEvents,
    reDecodeMissingTransactionEvents,
    addTransactionEvent,
    editTransactionEvent,
    deleteTransactionEvent
  };
};

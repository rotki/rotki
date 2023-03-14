import { type ActionResult } from '@rotki/common/lib/data';
import {
  snakeCaseTransformer,
  getUpdatedKey
} from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validTaskStatus,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import { type CollectionResponse } from '@/types/collection';
import { type EntryWithMeta } from '@/types/history/meta';
import {
  type AddTransactionHashPayload,
  type AddressesAndEvmChainPayload,
  type EthTransaction,
  EthTransactionCollectionResponse,
  EthTransactionEventDetail,
  type NewEthTransactionEvent,
  type TransactionEventRequestPayload,
  type TransactionRequestPayload
} from '@/types/history/tx';
import { nonEmptyProperties } from '@/utils/data';
import { type PendingTask } from '@/types/task';

export const useTransactionsApi = () => {
  const internalEthTransactions = async <T>(
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
            payload.orderByAttributes?.map(item =>
              getUpdatedKey(item, false)
            ) ?? []
        })
      ),
      {
        paramsSerializer,
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

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
    event: NewEthTransactionEvent
  ): Promise<{ identifier: number }> => {
    const response = await api.instance.put<
      ActionResult<{ identifier: number }>
    >('/history/events', snakeCaseTransformer(event), {
      validateStatus: validStatus
    });

    return handleResponse(response);
  };

  const editTransactionEvent = async (
    event: NewEthTransactionEvent
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
    identifiers: number[]
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/history/events',
      {
        data: snakeCaseTransformer({ identifiers }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const getEventDetails = async (
    identifier: number
  ): Promise<EthTransactionEventDetail> => {
    const response = await api.instance.get<
      ActionResult<EthTransactionEventDetail>
    >('/history/events/details', {
      params: snakeCaseTransformer({ identifier })
    });
    return EthTransactionEventDetail.parse(handleResponse(response));
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

  return {
    fetchEthTransactionsTask,
    fetchEthTransactions,
    deleteEthTransactions,
    fetchEthTransactionEvents,
    reDecodeMissingTransactionEvents,
    addTransactionEvent,
    editTransactionEvent,
    deleteTransactionEvent,
    getEventDetails,
    addTransactionHash
  };
};

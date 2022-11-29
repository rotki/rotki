import { type ActionResult } from '@rotki/common/lib/data';
import { axiosSnakeCaseTransformer } from '@/services/axios-tranformers';
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
  type NewTrade,
  type Trade,
  TradeCollectionResponse,
  type TradeRequestPayload
} from '@/types/history/trades';

export const useTradesApi = () => {
  const internalTrades = async <T>(
    payload: TradeRequestPayload,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.get<ActionResult<T>>('/trades', {
      params: axiosSnakeCaseTransformer({
        asyncQuery,
        ...payload
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService
    });

    return handleResponse(response);
  };

  const getTradesTask = async (
    payload: TradeRequestPayload
  ): Promise<PendingTask> => {
    return internalTrades<PendingTask>(payload, true);
  };

  const getTrades = async (
    payload: TradeRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<Trade>>> => {
    const response = await internalTrades<
      CollectionResponse<EntryWithMeta<Trade>>
    >(payload, false);

    return TradeCollectionResponse.parse(response);
  };

  const addExternalTrade = async (trade: NewTrade): Promise<Trade> => {
    const response = await api.instance.put<ActionResult<Trade>>(
      '/trades',
      axiosSnakeCaseTransformer(trade),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const editExternalTrade = async (trade: Trade): Promise<Trade> => {
    const response = await api.instance.patch<ActionResult<Trade>>(
      '/trades',
      axiosSnakeCaseTransformer(trade),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteExternalTrade = async (tradesIds: string[]): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/trades',
      {
        data: axiosSnakeCaseTransformer({ tradesIds }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getTradesTask,
    getTrades,
    addExternalTrade,
    editExternalTrade,
    deleteExternalTrade
  };
};

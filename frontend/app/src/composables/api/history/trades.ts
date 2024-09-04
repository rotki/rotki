import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import {
  handleResponse,
  paramsSerializer,
  validStatus,
  validWithParamsSessionAndExternalService,
} from '@/services/utils';
import { type NewTrade, type Trade, TradeCollectionResponse, type TradeRequestPayload } from '@/types/history/trade';
import type { CollectionResponse } from '@/types/collection';
import type { EntryWithMeta } from '@/types/history/meta';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';

interface UseTradesApiReturn {
  getTradesTask: (payload: TradeRequestPayload) => Promise<PendingTask>;
  getTrades: (payload: TradeRequestPayload) => Promise<CollectionResponse<EntryWithMeta<Trade>>>;
  addExternalTrade: (trade: NewTrade) => Promise<Trade>;
  editExternalTrade: (trade: Trade) => Promise<Trade>;
  deleteExternalTrade: (tradesIds: string[]) => Promise<boolean>;
}

export function useTradesApi(): UseTradesApiReturn {
  const internalTrades = async <T>(payload: TradeRequestPayload, asyncQuery: boolean): Promise<T> => {
    const response = await api.instance.get<ActionResult<T>>('/trades', {
      params: snakeCaseTransformer({
        asyncQuery,
        ...payload,
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const getTradesTask = (payload: TradeRequestPayload): Promise<PendingTask> =>
    internalTrades<PendingTask>(payload, true);

  const getTrades = async (payload: TradeRequestPayload): Promise<CollectionResponse<EntryWithMeta<Trade>>> => {
    const response = await internalTrades<CollectionResponse<EntryWithMeta<Trade>>>(payload, false);

    return TradeCollectionResponse.parse(response);
  };

  const addExternalTrade = async (trade: NewTrade): Promise<Trade> => {
    const response = await api.instance.put<ActionResult<Trade>>('/trades', snakeCaseTransformer(trade), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const editExternalTrade = async (trade: Trade): Promise<Trade> => {
    const response = await api.instance.patch<ActionResult<Trade>>('/trades', snakeCaseTransformer(trade), {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const deleteExternalTrade = async (tradesIds: string[]): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>('/trades', {
      data: snakeCaseTransformer({ tradesIds }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  return {
    getTradesTask,
    getTrades,
    addExternalTrade,
    editExternalTrade,
    deleteExternalTrade,
  };
}

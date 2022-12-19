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
import {
  type LedgerAction,
  LedgerActionCollectionResponse,
  type LedgerActionRequestPayload,
  type NewLedgerAction
} from '@/types/history/ledger-actions';
import { type EntryWithMeta } from '@/types/history/meta';

export const useLedgerActionsApi = () => {
  const internalLedgerActions = async <T>(
    payload: LedgerActionRequestPayload,
    asyncQuery: boolean
  ): Promise<T> => {
    const response = await api.instance.get<ActionResult<T>>('/ledgeractions', {
      params: axiosSnakeCaseTransformer({
        asyncQuery,
        ...payload
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService
    });

    return handleResponse(response);
  };

  const getLedgerActionsTask = async (
    payload: LedgerActionRequestPayload
  ): Promise<PendingTask> => {
    return internalLedgerActions<PendingTask>(payload, true);
  };

  const getLedgerActions = async (
    payload: LedgerActionRequestPayload
  ): Promise<CollectionResponse<EntryWithMeta<LedgerAction>>> => {
    const response = await internalLedgerActions<
      CollectionResponse<EntryWithMeta<LedgerAction>>
    >(payload, false);

    return LedgerActionCollectionResponse.parse(response);
  };

  const addLedgerAction = async (
    ledgerAction: NewLedgerAction
  ): Promise<LedgerAction> => {
    const response = await api.instance.put<ActionResult<LedgerAction>>(
      '/ledgeractions',
      axiosSnakeCaseTransformer(ledgerAction),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const editLedgerAction = async (
    ledgerAction: LedgerAction
  ): Promise<LedgerAction> => {
    const response = await api.instance.patch<ActionResult<LedgerAction>>(
      '/ledgeractions',
      axiosSnakeCaseTransformer(ledgerAction),
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const deleteLedgerAction = async (
    identifiers: number[]
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/ledgeractions',
      {
        data: axiosSnakeCaseTransformer({ identifiers }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  return {
    getLedgerActionsTask,
    getLedgerActions,
    addLedgerAction,
    editLedgerAction,
    deleteLedgerAction
  };
};

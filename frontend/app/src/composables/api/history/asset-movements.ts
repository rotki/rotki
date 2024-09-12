import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, paramsSerializer, validWithParamsSessionAndExternalService } from '@/services/utils';
import {
  type AssetMovement,
  AssetMovementCollectionResponse,
  type AssetMovementRequestPayload,
} from '@/types/history/asset-movements';
import type { CollectionResponse } from '@/types/collection';
import type { EntryWithMeta } from '@/types/history/meta';
import type { ActionResult } from '@rotki/common';
import type { PendingTask } from '@/types/task';

interface UseAssetMovementsApiReturn {
  getAssetMovements: (payload: AssetMovementRequestPayload) => Promise<CollectionResponse<EntryWithMeta<AssetMovement>>>;
  getAssetMovementsTask: (payload: AssetMovementRequestPayload) => Promise<PendingTask>;
}

export function useAssetMovementsApi(): UseAssetMovementsApiReturn {
  const internalAssetMovements = async <T>(payload: AssetMovementRequestPayload, asyncQuery: boolean): Promise<T> => {
    const response = await api.instance.get<ActionResult<T>>('/asset_movements', {
      params: snakeCaseTransformer({
        asyncQuery,
        ...payload,
      }),
      paramsSerializer,
      validateStatus: validWithParamsSessionAndExternalService,
    });

    return handleResponse(response);
  };

  const getAssetMovementsTask = (payload: AssetMovementRequestPayload): Promise<PendingTask> =>
    internalAssetMovements<PendingTask>(payload, true);

  const getAssetMovements = async (
    payload: AssetMovementRequestPayload,
  ): Promise<CollectionResponse<EntryWithMeta<AssetMovement>>> => {
    const response = await internalAssetMovements<CollectionResponse<EntryWithMeta<AssetMovement>>>(payload, false);

    return AssetMovementCollectionResponse.parse(response);
  };

  return {
    getAssetMovements,
    getAssetMovementsTask,
  };
}

import { type ActionResult } from '@rotki/common/lib/data';
import { type SyncAction } from '@/types/session/sync';
import { type PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import {
  handleResponse,
  validWithParamsSessionAndExternalService
} from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';

export const useSyncApi = () => {
  const forceSync = async (action: SyncAction): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/premium/sync',
      snakeCaseTransformer({ asyncQuery: true, action }),
      {
        validateStatus: validWithParamsSessionAndExternalService
      }
    );

    return handleResponse(response);
  };

  return {
    forceSync
  };
};

import { snakeCaseTransformer } from '@/services/axios-tranformers';
import { handleResponse, validWithParamsSessionAndExternalService } from '@/services/utils';
import { api } from '@/services/rotkehlchen-api';
import type { ActionResult } from '@rotki/common';
import type { SyncAction } from '@/types/session/sync';
import type { PendingTask } from '@/types/task';

interface UseSyncApiReturn { forceSync: (action: SyncAction) => Promise<PendingTask> }

export function useSyncApi(): UseSyncApiReturn {
  const forceSync = async (action: SyncAction): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/premium/sync',
      snakeCaseTransformer({ asyncQuery: true, action }),
      {
        validateStatus: validWithParamsSessionAndExternalService,
      },
    );

    return handleResponse(response);
  };

  return {
    forceSync,
  };
}

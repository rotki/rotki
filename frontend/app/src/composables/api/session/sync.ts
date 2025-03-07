import type { SyncAction } from '@/types/session/sync';
import type { PendingTask } from '@/types/task';
import type { ActionResult } from '@rotki/common';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithParamsSessionAndExternalService } from '@/services/utils';

interface UseSyncApiReturn { forceSync: (action: SyncAction) => Promise<PendingTask> }

export function useSyncApi(): UseSyncApiReturn {
  const forceSync = async (action: SyncAction): Promise<PendingTask> => {
    const response = await api.instance.put<ActionResult<PendingTask>>(
      '/premium/sync',
      snakeCaseTransformer({ action, asyncQuery: true }),
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

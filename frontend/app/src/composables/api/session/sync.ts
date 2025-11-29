import type { SyncAction } from '@/types/session/sync';
import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/types/task';

interface UseSyncApiReturn { forceSync: (action: SyncAction) => Promise<PendingTask> }

export function useSyncApi(): UseSyncApiReturn {
  const forceSync = async (action: SyncAction): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/premium/sync',
      { action, asyncQuery: true },
      {
        validStatuses: VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE,
      },
    );

    return PendingTaskSchema.parse(response);
  };

  return {
    forceSync,
  };
}

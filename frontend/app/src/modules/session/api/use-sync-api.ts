import { api } from '@/modules/core/api/rotki-api';
import { VALID_WITH_PARAMS_SESSION_AND_EXTERNAL_SERVICE, VALID_WITH_SESSION_AND_EXTERNAL_SERVICE } from '@/modules/core/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/modules/core/tasks/types';
import { type RemoteBackup, RemoteBackupDeletion, RemoteBackupResponse, type SyncAction } from '@/modules/session/sync';

interface DeleteRemoteBackupPayload {
  /** The hash of the backup the user reviewed; the server keeps a backup that changed since. */
  dataHash: string;
  /** Turn off this device's automatic backup, so it does not upload one right after. */
  disableSync: boolean;
}

interface UseSyncApiReturn {
  forceSync: (action: SyncAction) => Promise<PendingTask>;
  /** The backup stored on the rotki server, or null when there is none. */
  fetchRemoteBackup: () => Promise<RemoteBackup | null>;
  /** Deletes the backup stored on the rotki server, and says whether automatic backup is still on. */
  deleteRemoteBackup: (payload: DeleteRemoteBackupPayload) => Promise<RemoteBackupDeletion>;
}

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

  const fetchRemoteBackup = async (): Promise<RemoteBackup | null> => {
    const response = await api.get<RemoteBackupResponse>('/premium/sync', {
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return RemoteBackupResponse.parse(response).backup;
  };

  const deleteRemoteBackup = async (payload: DeleteRemoteBackupPayload): Promise<RemoteBackupDeletion> => {
    const response = await api.delete<RemoteBackupDeletion>('/premium/sync', {
      body: payload,
      validStatuses: VALID_WITH_SESSION_AND_EXTERNAL_SERVICE,
    });
    return RemoteBackupDeletion.parse(response);
  };

  return {
    deleteRemoteBackup,
    fetchRemoteBackup,
    forceSync,
  };
}

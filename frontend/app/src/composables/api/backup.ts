import { api } from '@/modules/api/rotki-api';
import { VALID_WITH_SESSION_STATUS } from '@/modules/api/utils';
import { type DatabaseInfo, DatabaseInfoSchema } from '@/types/backup';

interface UseBackupApiReturn {
  info: () => Promise<DatabaseInfo>;
  createBackup: () => Promise<string>;
  deleteBackup: (files: string[]) => Promise<boolean>;
  fileUrl: (file: string) => string;
}

export function useBackupApi(): UseBackupApiReturn {
  const info = async (): Promise<DatabaseInfo> => {
    const response = await api.get<DatabaseInfo>('/database/info', {
      validStatuses: VALID_WITH_SESSION_STATUS,
    });

    return DatabaseInfoSchema.parse(response);
  };

  const createBackup = async (): Promise<string> => api.put<string>('/database/backups', null, {
    validStatuses: VALID_WITH_SESSION_STATUS,
  });

  const deleteBackup = async (files: string[]): Promise<boolean> => api.delete<boolean>('/database/backups', {
    body: {
      files,
    },
    validStatuses: VALID_WITH_SESSION_STATUS,
  });

  function fileUrl(file: string): string {
    return api.buildUrl('database/backups', { file });
  }

  return {
    createBackup,
    deleteBackup,
    fileUrl,
    info,
  };
}

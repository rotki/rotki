import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';
import {
  CreateDatabaseResponse,
  type DatabaseInfo,
  DatabaseInfoResponse,
  DeleteDatabaseResponse
} from '@/types/backup';

export const useBackupApi = () => {
  const info = async (): Promise<DatabaseInfo> => {
    const response = await api.instance.get<DatabaseInfoResponse>(
      '/database/info',
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response, response =>
      DatabaseInfoResponse.parse(response.data)
    );
  };

  const createBackup = async (): Promise<string> => {
    const response = await api.instance.put<CreateDatabaseResponse>(
      '/database/backups',
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response, response =>
      CreateDatabaseResponse.parse(response.data)
    );
  };

  const deleteBackup = async (files: string[]): Promise<boolean> => {
    const response = await api.instance.delete<DeleteDatabaseResponse>(
      '/database/backups',
      {
        data: {
          files
        },
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response, response =>
      DeleteDatabaseResponse.parse(response.data)
    );
  };

  function fileUrl(file: string): string {
    return `${api.instance.defaults.baseURL}/database/backups?file=${file}`;
  }
  return {
    info,
    createBackup,
    deleteBackup,
    fileUrl
  };
};

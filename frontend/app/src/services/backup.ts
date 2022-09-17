import { basicAxiosTransformer } from '@/services/consts';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validWithSessionStatus } from '@/services/utils';
import {
  CreateDatabaseResponse,
  DatabaseInfo,
  DatabaseInfoResponse,
  DeleteDatabaseResponse
} from '@/types/backup';

export const useBackupApi = () => {
  async function info(): Promise<DatabaseInfo> {
    const response = await api.instance.get<DatabaseInfoResponse>(
      '/database/info',
      {
        validateStatus: validWithSessionStatus,
        transformResponse: basicAxiosTransformer
      }
    );

    return handleResponse(response, response =>
      DatabaseInfoResponse.parse(response.data)
    );
  }

  async function createBackup(): Promise<string> {
    const response = await api.instance.put<CreateDatabaseResponse>(
      '/database/backups',
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response, response =>
      CreateDatabaseResponse.parse(response.data)
    );
  }

  async function deleteBackup(files: string[]): Promise<boolean> {
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
  }

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

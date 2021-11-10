import { AxiosInstance } from 'axios';
import { setupTransformer } from '@/services/axios-tranformers';
import {
  CreateDatabaseResponse,
  DatabaseInfo,
  DatabaseInfoResponse,
  DeleteDatabaseResponse
} from '@/services/backup/types';
import { handleResponse, validWithSessionStatus } from '@/services/utils';

export class BackupApi {
  private static transformer = setupTransformer([]);
  constructor(private readonly axios: AxiosInstance) {}

  async info(): Promise<DatabaseInfo> {
    const response = await this.axios.get<DatabaseInfoResponse>(
      '/database/info',
      {
        validateStatus: validWithSessionStatus,
        transformResponse: BackupApi.transformer
      }
    );

    return handleResponse(response, response =>
      DatabaseInfoResponse.parse(response.data)
    );
  }

  async createBackup(): Promise<string> {
    const response = await this.axios.put<CreateDatabaseResponse>(
      '/database/backups',
      {
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response, response =>
      CreateDatabaseResponse.parse(response.data)
    );
  }

  async deleteBackup(file: string): Promise<boolean> {
    const response = await this.axios.delete<DeleteDatabaseResponse>(
      '/database/backups',
      {
        data: {
          file
        },
        validateStatus: validWithSessionStatus
      }
    );

    return handleResponse(response, response =>
      DeleteDatabaseResponse.parse(response.data)
    );
  }

  fileUrl(file: string): string {
    return `${this.axios.defaults.baseURL}/database/backups?file=${file}`;
  }
}

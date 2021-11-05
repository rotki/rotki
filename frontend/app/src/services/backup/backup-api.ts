import { ActionResult } from '@rotki/common/lib/data';
import { AxiosInstance } from 'axios';
import { setupTransformer } from '@/services/axios-tranformers';
import {
  CreateDatabaseResponse,
  DatabaseInfo,
  DatabaseInfoResponse,
  DeleteDatabaseResponse
} from '@/services/backup/types';
import {
  handleResponse,
  validStatus,
  validWithSessionStatus
} from '@/services/utils';
import { ActionStatus } from '@/store/types';
import { assert } from '@/utils/assertions';

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
    const response = await this.axios.get<CreateDatabaseResponse>(
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

  async downloadFile(file: string): Promise<ActionStatus> {
    try {
      const response = await this.axios.get('/database/backups', {
        params: {
          file: file
        },
        responseType: 'blob',
        validateStatus: validStatus
      });
      if (response.status === 200) {
        const url = window.URL.createObjectURL(response.data);
        const link = document.createElement('a');
        link.id = 'db-download-link';
        link.href = url;
        const filename = new URL(file).pathname.split('/').pop();
        assert(filename);
        link.setAttribute('download', filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        return { success: true };
      }

      const body = await (response.data as Blob).text();
      const result: ActionResult<null> = JSON.parse(body);

      return { success: false, message: result.message };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  }
}

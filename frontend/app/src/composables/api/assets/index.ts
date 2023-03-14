import { type ActionResult } from '@rotki/common/lib/data';
import { snakeCaseTransformer } from '@/services/axios-tranformers';
import {
  handleResponse,
  validFileOperationStatus,
  validStatus,
  validWithoutSessionStatus
} from '@/services/utils';
import { assert } from '@/utils/assertions';
import { api } from '@/services/rotkehlchen-api';
import { downloadFileByUrl } from '@/utils/download';
import { type ActionStatus } from '@/types/action';
import { type ConflictResolution } from '@/types/asset';
import { type PendingTask } from '@/types/task';

export const useAssetsApi = () => {
  const checkForAssetUpdate = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/assets/updates',
      {
        params: snakeCaseTransformer({ asyncQuery: true }),
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  const performUpdate = async (
    version: number,
    conflicts?: ConflictResolution
  ): Promise<PendingTask> => {
    const data = {
      async_query: true,
      up_to_version: version,
      conflicts
    };

    const response = await api.instance.post<ActionResult<PendingTask>>(
      '/assets/updates',
      data,
      {
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const mergeAssets = async (
    sourceIdentifier: string,
    targetAsset: string
  ): Promise<true> => {
    const data = snakeCaseTransformer({
      sourceIdentifier,
      targetAsset
    });
    const response = await api.instance.put<ActionResult<true>>(
      '/assets/replace',
      data,
      {
        validateStatus: validStatus
      }
    );
    return handleResponse(response);
  };

  const restoreAssetsDatabase = async (
    reset: 'hard' | 'soft',
    ignoreWarnings: boolean
  ): Promise<boolean> => {
    const response = await api.instance.delete<ActionResult<boolean>>(
      '/assets/updates',
      {
        data: snakeCaseTransformer({ reset, ignoreWarnings }),
        validateStatus: validStatus
      }
    );

    return handleResponse(response);
  };

  const importCustom = async (
    file: File,
    upload = false
  ): Promise<ActionResult<boolean>> => {
    if (upload) {
      const data = new FormData();
      data.append('file', file);
      const response = await api.instance.post('/assets/user', data, {
        validateStatus: validFileOperationStatus,
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      return handleResponse(response);
    }

    const response = await api.instance.put(
      '/assets/user',
      { action: 'upload', file: file.path },
      {
        validateStatus: validFileOperationStatus
      }
    );
    return handleResponse(response);
  };

  const exportCustom = async (directory?: string): Promise<ActionStatus> => {
    try {
      if (!directory) {
        const response = await api.instance.put(
          '/assets/user',
          { action: 'download' },
          {
            responseType: 'blob',
            validateStatus: validFileOperationStatus
          }
        );
        if (response.status === 200) {
          const url = window.URL.createObjectURL(response.request.response);
          downloadFileByUrl(url, 'assets.zip');
          return { success: true };
        }
        const body = await (response.data as Blob).text();
        const result: ActionResult<null> = JSON.parse(body);

        return { success: false, message: result.message };
      }
      const response = await api.instance.put<ActionResult<{ file: string }>>(
        '/assets/user',
        { action: 'download', destination: directory },
        {
          validateStatus: validFileOperationStatus
        }
      );
      const data = handleResponse(response);
      assert(data.file);
      return {
        success: true
      };
    } catch (e: any) {
      return { success: false, message: e.message };
    }
  };

  const fetchNfts = async (ignoreCache: boolean): Promise<PendingTask> => {
    const params = Object.assign(
      {
        asyncQuery: true
      },
      ignoreCache ? { ignoreCache } : {}
    );
    const response = await api.instance.get<ActionResult<PendingTask>>(
      '/nfts',
      {
        params: snakeCaseTransformer(params),
        validateStatus: validWithoutSessionStatus
      }
    );

    return handleResponse(response);
  };

  return {
    checkForAssetUpdate,
    performUpdate,
    mergeAssets,
    restoreAssetsDatabase,
    importCustom,
    exportCustom,
    fetchNfts
  };
};

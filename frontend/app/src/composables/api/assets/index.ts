import type { ActionStatus } from '@/types/action';
import type { ConflictResolution } from '@/types/asset';
import type { PendingTask } from '@/types/task';
import { snakeCaseTransformer } from '@/services/axios-transformers';
import { api } from '@/services/rotkehlchen-api';
import { handleResponse, validFileOperationStatus, validStatus, validWithoutSessionStatus } from '@/services/utils';
import { downloadFileByBlobResponse } from '@/utils/download';
import { type ActionResult, assert } from '@rotki/common';

interface UseAssetApiReturn {
  checkForAssetUpdate: () => Promise<PendingTask>;
  performUpdate: (version: number, conflicts?: ConflictResolution) => Promise<PendingTask>;
  mergeAssets: (sourceIdentifier: string, targetAsset: string) => Promise<true>;
  restoreAssetsDatabase: (reset: 'hard' | 'soft', ignoreWarnings: boolean) => Promise<PendingTask>;
  importCustom: (file: File | string) => Promise<PendingTask>;
  exportCustom: (directory?: string) => Promise<ActionStatus>;
  fetchNfts: (ignoreCache: boolean) => Promise<PendingTask>;
}

export function useAssetsApi(): UseAssetApiReturn {
  const checkForAssetUpdate = async (): Promise<PendingTask> => {
    const response = await api.instance.get<ActionResult<PendingTask>>('/assets/updates', {
      params: snakeCaseTransformer({ asyncQuery: true }),
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  const performUpdate = async (version: number, conflicts?: ConflictResolution): Promise<PendingTask> => {
    const data = {
      async_query: true,
      conflicts,
      up_to_version: version,
    };

    const response = await api.instance.post<ActionResult<PendingTask>>('/assets/updates', data, {
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const mergeAssets = async (sourceIdentifier: string, targetAsset: string): Promise<true> => {
    const data = snakeCaseTransformer({
      sourceIdentifier,
      targetAsset,
    });
    const response = await api.instance.put<ActionResult<true>>('/assets/replace', data, {
      validateStatus: validStatus,
    });
    return handleResponse(response);
  };

  const restoreAssetsDatabase = async (reset: 'hard' | 'soft', ignoreWarnings: boolean): Promise<PendingTask> => {
    const response = await api.instance.delete<ActionResult<PendingTask>>('/assets/updates', {
      data: snakeCaseTransformer({
        asyncQuery: true,
        ignoreWarnings,
        reset,
      }),
      validateStatus: validStatus,
    });

    return handleResponse(response);
  };

  const importCustom = async (file: File | string): Promise<PendingTask> => {
    if (typeof file !== 'string') {
      const data = new FormData();
      data.append('file', file);
      data.append('async_query', 'true');

      const response = await api.instance.post('/assets/user', data, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        validateStatus: validFileOperationStatus,
      });
      return handleResponse(response);
    }

    const response = await api.instance.put(
      '/assets/user',
      snakeCaseTransformer({
        action: 'upload',
        asyncQuery: true,
        file,
      }),
      {
        validateStatus: validFileOperationStatus,
      },
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
            validateStatus: validFileOperationStatus,
          },
        );
        if (response.status === 200) {
          downloadFileByBlobResponse(response, 'assets.zip');
          return { success: true };
        }
        const body = await (response.data as Blob).text();
        const result: ActionResult<null> = JSON.parse(body);

        return { message: result.message, success: false };
      }
      const response = await api.instance.put<ActionResult<{ file: string }>>(
        '/assets/user',
        { action: 'download', destination: directory },
        {
          validateStatus: validFileOperationStatus,
        },
      );
      const data = handleResponse(response);
      assert(data.file);
      return {
        success: true,
      };
    }
    catch (error: any) {
      return { message: error.message, success: false };
    }
  };

  const fetchNfts = async (ignoreCache: boolean): Promise<PendingTask> => {
    const params = Object.assign(
      {
        asyncQuery: true,
      },
      ignoreCache ? { ignoreCache } : {},
    );
    const response = await api.instance.get<ActionResult<PendingTask>>('/nfts', {
      params: snakeCaseTransformer(params),
      validateStatus: validWithoutSessionStatus,
    });

    return handleResponse(response);
  };

  return {
    checkForAssetUpdate,
    exportCustom,
    fetchNfts,
    importCustom,
    mergeAssets,
    performUpdate,
    restoreAssetsDatabase,
  };
}

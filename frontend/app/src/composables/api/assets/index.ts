import type { ActionStatus } from '@/types/action';
import type { ConflictResolution } from '@/types/asset';
import { api } from '@/modules/api/rotki-api';
import { VALID_FILE_OPERATION_STATUS, VALID_WITHOUT_SESSION_STATUS } from '@/modules/api/utils';
import { type PendingTask, PendingTaskSchema } from '@/types/task';
import { downloadFileByUrl } from '@/utils/download';
import { getFilename } from '@/utils/file';

interface UseAssetApiReturn {
  checkForAssetUpdate: () => Promise<PendingTask>;
  performUpdate: (version: number, conflicts?: ConflictResolution) => Promise<PendingTask>;
  mergeAssets: (sourceIdentifier: string, targetAsset: string) => Promise<true>;
  restoreAssetsDatabase: (reset: 'hard' | 'soft', ignoreWarnings: boolean) => Promise<PendingTask>;
  importCustom: (file: File | string) => Promise<PendingTask>;
  exportCustom: (directory?: string) => Promise<PendingTask>;
  downloadCustomAssets: (filePath: string) => Promise<ActionStatus>;
  fetchNfts: (ignoreCache: boolean) => Promise<PendingTask>;
}

export function useAssetsApi(): UseAssetApiReturn {
  const checkForAssetUpdate = async (): Promise<PendingTask> => {
    const response = await api.get<PendingTask>('/assets/updates', {
      query: { asyncQuery: true },
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    });
    return PendingTaskSchema.parse(response);
  };

  const performUpdate = async (version: number, conflicts?: ConflictResolution): Promise<PendingTask> => {
    const response = await api.post<PendingTask>('/assets/updates', {
      asyncQuery: true,
      conflicts,
      upToVersion: version,
    }, { skipSnakeCase: ['conflicts'] });
    return PendingTaskSchema.parse(response);
  };

  const mergeAssets = async (sourceIdentifier: string, targetAsset: string): Promise<true> => api.put<true>('/assets/replace', {
    sourceIdentifier,
    targetAsset,
  });

  const restoreAssetsDatabase = async (reset: 'hard' | 'soft', ignoreWarnings: boolean): Promise<PendingTask> => {
    const response = await api.delete<PendingTask>('/assets/updates', {
      body: {
        asyncQuery: true,
        ignoreWarnings,
        reset,
      },
    });
    return PendingTaskSchema.parse(response);
  };

  const importCustom = async (file: File | string): Promise<PendingTask> => {
    if (typeof file !== 'string') {
      const data = new FormData();
      data.append('file', file);
      data.append('async_query', 'true');

      const response = await api.post<PendingTask>('/assets/user', data, {
        validStatuses: VALID_FILE_OPERATION_STATUS,
      });
      return PendingTaskSchema.parse(response);
    }

    const response = await api.put<PendingTask>(
      '/assets/user',
      {
        action: 'upload',
        asyncQuery: true,
        file,
      },
      {
        validStatuses: VALID_FILE_OPERATION_STATUS,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const exportCustom = async (directory?: string): Promise<PendingTask> => {
    const response = await api.put<PendingTask>(
      '/assets/user',
      {
        asyncQuery: true,
        destination: directory,
      },
      {
        validStatuses: VALID_FILE_OPERATION_STATUS,
      },
    );
    return PendingTaskSchema.parse(response);
  };

  const downloadCustomAssets = async (filePath: string): Promise<ActionStatus> => {
    try {
      const fullUrl = api.buildUrl('assets/user/download', { filePath });
      downloadFileByUrl(fullUrl, getFilename(filePath));
      return { success: true };
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
    const response = await api.get<PendingTask>('/nfts', {
      query: params,
      validStatuses: VALID_WITHOUT_SESSION_STATUS,
    });
    return PendingTaskSchema.parse(response);
  };

  return {
    checkForAssetUpdate,
    downloadCustomAssets,
    exportCustom,
    fetchNfts,
    importCustom,
    mergeAssets,
    performUpdate,
    restoreAssetsDatabase,
  };
}

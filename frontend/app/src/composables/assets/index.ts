import type { ActionStatus } from '@/types/action';
import type {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdatePayload,
  AssetUpdateResult,
} from '@/types/asset';
import type { TaskMeta } from '@/types/task';
import { useAssetsApi } from '@/composables/api/assets';
import { useInterop } from '@/composables/electron-interop';
import { useNotificationsStore } from '@/store/notifications';
import { useTaskStore } from '@/store/tasks';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import { TaskType } from '@/types/task-type';
import { isTaskCancelled } from '@/utils';
import { logger } from '@/utils/logging';

interface UseAssetsReturn {
  checkForUpdate: () => Promise<AssetUpdateCheckResult>;
  applyUpdates: (payload: AssetUpdatePayload) => Promise<ApplyUpdateResult>;
  mergeAssets: (payload: AssetMergePayload) => Promise<ActionStatus<string | ValidationErrors>>;
  importCustomAssets: (file: File) => Promise<ActionStatus>;
  exportCustomAssets: () => Promise<ActionStatus>;
  restoreAssetsDatabase: (resetType: 'hard' | 'soft') => Promise<ActionStatus>;
}

export function useAssets(): UseAssetsReturn {
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { appSession, getPath, openDirectory } = useInterop();
  const {
    checkForAssetUpdate,
    exportCustom,
    importCustom,
    mergeAssets: mergeAssetsCaller,
    performUpdate,
    restoreAssetsDatabase: restoreAssetsDatabaseCaller,
  } = useAssetsApi();

  const { notify } = useNotificationsStore();

  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await checkForAssetUpdate();
      const { result } = await awaitTask<AssetDBVersion, TaskMeta>(taskId, taskType, {
        title: t('actions.assets.versions.task.title'),
      });

      return {
        updateAvailable: result.local < result.remote && result.newChanges > 0,
        versions: result,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.assets.versions.task.title');
        const description = t('actions.assets.versions.error.description', {
          message: error.message,
        }).toString();

        notify({
          display: true,
          message: description,
          title,
        });
      }
      return {
        updateAvailable: false,
      };
    }
  };

  const applyUpdates = async ({ resolution, version }: AssetUpdatePayload): Promise<ApplyUpdateResult> => {
    try {
      const { taskId } = await performUpdate(version, resolution);
      const { result } = await awaitTask<AssetUpdateResult, TaskMeta>(taskId, TaskType.ASSET_UPDATE_PERFORM, {
        title: t('actions.assets.update.task.title'),
      });

      if (typeof result === 'boolean') {
        return {
          done: true,
        };
      }
      return {
        conflicts: result,
        done: false,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.assets.update.task.title');
        const description = t('actions.assets.update.error.description', {
          message: error.message,
        }).toString();
        notify({
          display: true,
          message: description,
          title,
        });
      }
      return {
        done: false,
      };
    }
  };

  const mergeAssets = async ({
    sourceIdentifier,
    targetIdentifier,
  }: AssetMergePayload): Promise<ActionStatus<string | ValidationErrors>> => {
    try {
      const success = await mergeAssetsCaller(sourceIdentifier, targetIdentifier);
      return {
        success,
      };
    }
    catch (error: any) {
      let message: string | ValidationErrors = error.message;
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors({ sourceIdentifier, targetIdentifier });

      return {
        message,
        success: false,
      };
    }
  };

  const importCustomAssets = async (file: File): Promise<ActionStatus> => {
    try {
      const path = getPath(file);
      const { taskId } = await importCustom(path ?? file);
      await awaitTask<boolean, TaskMeta>(taskId, TaskType.IMPORT_ASSET, {
        title: t('actions.assets.import.task.title'),
      });

      return {
        success: true,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      return {
        message: error.message,
        success: false,
      };
    }
  };

  const exportCustomAssets = async (): Promise<ActionStatus> => {
    try {
      let file: string | undefined;
      if (appSession) {
        const directory = await openDirectory(t('common.select_directory').toString());
        if (!directory) {
          return {
            message: t('assets.backup.missing_directory'),
            success: false,
          };
        }
        file = directory;
      }
      return await exportCustom(file);
    }
    catch (error: any) {
      return {
        message: error.message,
        success: false,
      };
    }
  };

  const restoreAssetsDatabase = async (resetType: 'hard' | 'soft'): Promise<ActionStatus> => {
    try {
      const { taskId } = await restoreAssetsDatabaseCaller(resetType, resetType === 'hard');
      await awaitTask<boolean, TaskMeta>(taskId, TaskType.RESET_ASSET, {
        title: t('actions.assets.reset.task.title'),
      });

      return {
        success: true,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error))
        logger.error(error);

      return {
        message: error.message,
        success: false,
      };
    }
  };

  return {
    applyUpdates,
    checkForUpdate,
    exportCustomAssets,
    importCustomAssets,
    mergeAssets,
    restoreAssetsDatabase,
  };
}

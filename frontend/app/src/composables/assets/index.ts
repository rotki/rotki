import { TaskType } from '@/types/task-type';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';
import type {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdatePayload,
  AssetUpdateResult,
} from '@/types/asset';
import type { TaskMeta } from '@/types/task';
import type { ActionStatus } from '@/types/action';

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
    performUpdate,
    mergeAssets: mergeAssetsCaller,
    importCustom,
    exportCustom,
    restoreAssetsDatabase: restoreAssetsDatabaseCaller,
  } = useAssetsApi();

  const { notify } = useNotificationsStore();

  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await checkForAssetUpdate();
      const { result } = await awaitTask<AssetDBVersion, TaskMeta>(taskId, taskType, {
        title: t('actions.assets.versions.task.title').toString(),
      });

      return {
        updateAvailable: result.local < result.remote && result.newChanges > 0,
        versions: result,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.assets.versions.task.title').toString();
        const description = t('actions.assets.versions.error.description', {
          message: error.message,
        }).toString();

        notify({
          title,
          message: description,
          display: true,
        });
      }
      return {
        updateAvailable: false,
      };
    }
  };

  const applyUpdates = async ({ version, resolution }: AssetUpdatePayload): Promise<ApplyUpdateResult> => {
    try {
      const { taskId } = await performUpdate(version, resolution);
      const { result } = await awaitTask<AssetUpdateResult, TaskMeta>(taskId, TaskType.ASSET_UPDATE_PERFORM, {
        title: t('actions.assets.update.task.title').toString(),
      });

      if (typeof result === 'boolean') {
        return {
          done: true,
        };
      }
      return {
        done: false,
        conflicts: result,
      };
    }
    catch (error: any) {
      if (!isTaskCancelled(error)) {
        const title = t('actions.assets.update.task.title').toString();
        const description = t('actions.assets.update.error.description', {
          message: error.message,
        }).toString();
        notify({
          title,
          message: description,
          display: true,
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
        success: false,
        message,
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
        success: false,
        message: error.message,
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
            success: false,
            message: t('assets.backup.missing_directory').toString(),
          };
        }
        file = directory;
      }
      return await exportCustom(file);
    }
    catch (error: any) {
      return {
        success: false,
        message: error.message,
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
        success: false,
        message: error.message,
      };
    }
  };

  return {
    checkForUpdate,
    applyUpdates,
    mergeAssets,
    importCustomAssets,
    exportCustomAssets,
    restoreAssetsDatabase,
  };
}

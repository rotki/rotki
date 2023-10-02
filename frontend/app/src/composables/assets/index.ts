import {
  type ApplyUpdateResult,
  type AssetDBVersion,
  type AssetMergePayload,
  type AssetUpdateCheckResult,
  type AssetUpdatePayload,
  type AssetUpdateResult
} from '@/types/asset';
import { type TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';
import { type ActionStatus } from '@/types/action';
import { ApiValidationError, type ValidationErrors } from '@/types/api/errors';

export const useAssets = () => {
  const { awaitTask } = useTaskStore();
  const { t } = useI18n();
  const { appSession, openDirectory } = useInterop();
  const {
    checkForAssetUpdate,
    performUpdate,
    mergeAssets: mergeAssetsCaller,
    importCustom,
    exportCustom
  } = useAssetsApi();

  const { notify } = useNotificationsStore();

  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await checkForAssetUpdate();
      const { result } = await awaitTask<AssetDBVersion, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.assets.versions.task.title').toString()
        }
      );

      return {
        updateAvailable: result.local < result.remote && result.newChanges > 0,
        versions: result
      };
    } catch (e: any) {
      const title = t('actions.assets.versions.task.title').toString();
      const description = t('actions.assets.versions.error.description', {
        message: e.message
      }).toString();
      notify({
        title,
        message: description,
        display: true
      });
      return {
        updateAvailable: false
      };
    }
  };

  const applyUpdates = async ({
    version,
    resolution
  }: AssetUpdatePayload): Promise<ApplyUpdateResult> => {
    try {
      const { taskId } = await performUpdate(version, resolution);
      const { result } = await awaitTask<AssetUpdateResult, TaskMeta>(
        taskId,
        TaskType.ASSET_UPDATE_PERFORM,
        {
          title: t('actions.assets.update.task.title').toString()
        }
      );

      if (typeof result === 'boolean') {
        return {
          done: true
        };
      }
      return {
        done: false,
        conflicts: result
      };
    } catch (e: any) {
      const title = t('actions.assets.update.task.title').toString();
      const description = t('actions.assets.update.error.description', {
        message: e.message
      }).toString();
      notify({
        title,
        message: description,
        display: true
      });
      return {
        done: false
      };
    }
  };

  const mergeAssets = async ({
    sourceIdentifier,
    targetIdentifier
  }: AssetMergePayload): Promise<ActionStatus<string | ValidationErrors>> => {
    try {
      const success = await mergeAssetsCaller(
        sourceIdentifier,
        targetIdentifier
      );
      return {
        success
      };
    } catch (e: any) {
      let message: string | ValidationErrors = e.message;
      if (e instanceof ApiValidationError) {
        message = e.getValidationErrors({ sourceIdentifier, targetIdentifier });
      }
      return {
        success: false,
        message
      };
    }
  };

  const importCustomAssets = async (file: File): Promise<ActionStatus> => {
    try {
      await importCustom(file, !appSession);
      return {
        success: true
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const exportCustomAssets = async (): Promise<ActionStatus> => {
    try {
      let file: string | undefined = undefined;
      if (appSession) {
        const directory = await openDirectory(
          t('common.select_directory').toString()
        );
        if (!directory) {
          return {
            success: false,
            message: t('assets.backup.missing_directory').toString()
          };
        }
        file = directory;
      }
      return await exportCustom(file);
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  return {
    checkForUpdate,
    applyUpdates,
    mergeAssets,
    importCustomAssets,
    exportCustomAssets
  };
};

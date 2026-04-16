import type {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdatePayload,
  AssetUpdateResult,
} from '@/modules/assets/types';
import type { ActionStatus } from '@/modules/core/common/action';
import type { TaskMeta } from '@/modules/core/tasks/types';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { TaskType } from '@/modules/core/tasks/task-type';
import { isActionableFailure, useTaskHandler } from '@/modules/core/tasks/use-task-handler';
import { useInterop } from '@/modules/shell/app/use-electron-interop';

interface ExportCustomAssetsResult {
  directory?: string;
  filePath: string;
}

interface UseAssetsReturn {
  checkForUpdate: () => Promise<AssetUpdateCheckResult>;
  applyUpdates: (payload: AssetUpdatePayload) => Promise<ApplyUpdateResult>;
  mergeAssets: (payload: AssetMergePayload) => Promise<ActionStatus<string | ValidationErrors>>;
  importCustomAssets: (file: File) => Promise<ActionStatus>;
  exportCustomAssets: () => Promise<ActionStatus | ExportCustomAssetsResult>;
  restoreAssetsDatabase: (resetType: 'hard' | 'soft') => Promise<ActionStatus>;
}

export function useAssets(): UseAssetsReturn {
  const { runTask } = useTaskHandler();
  const { t } = useI18n({ useScope: 'global' });
  const { appSession, getPath, openDirectory } = useInterop();
  const {
    checkForAssetUpdate,
    downloadCustomAssets,
    exportCustom,
    importCustom,
    mergeAssets: mergeAssetsCaller,
    performUpdate,
    restoreAssetsDatabase: restoreAssetsDatabaseCaller,
  } = useAssetsApi();

  const { notifyError } = useNotifications();

  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    const outcome = await runTask<AssetDBVersion, TaskMeta>(
      async () => checkForAssetUpdate(),
      { type: TaskType.ASSET_UPDATE, meta: { title: t('actions.assets.versions.task.title') } },
    );

    if (outcome.success) {
      return {
        updateAvailable: outcome.result.local < outcome.result.remote && outcome.result.newChanges > 0,
        versions: outcome.result,
      };
    }
    else if (isActionableFailure(outcome)) {
      const title = t('actions.assets.versions.task.title');
      const description = t('actions.assets.versions.error.description', {
        message: outcome.message,
      }).toString();

      notifyError(title, description);
    }
    return {
      updateAvailable: false,
    };
  };

  const applyUpdates = async ({ resolution, version }: AssetUpdatePayload): Promise<ApplyUpdateResult> => {
    const outcome = await runTask<AssetUpdateResult, TaskMeta>(
      async () => performUpdate(version, resolution),
      { type: TaskType.ASSET_UPDATE_PERFORM, meta: { title: t('actions.assets.update.task.title') } },
    );

    if (outcome.success) {
      if (typeof outcome.result === 'boolean') {
        return {
          done: true,
        };
      }
      return {
        conflicts: outcome.result,
        done: false,
      };
    }
    else if (isActionableFailure(outcome)) {
      const title = t('actions.assets.update.task.title');
      const description = t('actions.assets.update.error.description', {
        message: outcome.message,
      }).toString();
      notifyError(title, description);
    }
    return {
      done: false,
    };
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
    catch (error: unknown) {
      let message: string | ValidationErrors = getErrorMessage(error);
      if (error instanceof ApiValidationError)
        message = error.getValidationErrors({ sourceIdentifier, targetIdentifier });

      return {
        message,
        success: false,
      };
    }
  };

  const importCustomAssets = async (file: File): Promise<ActionStatus> => {
    const path = getPath(file);
    const outcome = await runTask<boolean, TaskMeta>(
      async () => importCustom(path ?? file),
      { type: TaskType.IMPORT_ASSET, meta: { title: t('actions.assets.import.task.title') } },
    );

    if (outcome.success) {
      return {
        success: true,
      };
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      return { message: outcome.message, success: false };
    }

    return { message: '', success: false };
  };

  const exportCustomAssets = async (): Promise<ActionStatus | ExportCustomAssetsResult> => {
    let directory: string | undefined;
    if (appSession) {
      const selectedDirectory = await openDirectory(t('common.select_directory').toString());
      if (!selectedDirectory) {
        return {
          message: t('assets.backup.missing_directory'),
          success: false,
        };
      }
      directory = selectedDirectory;
    }

    const outcome = await runTask<{ filePath: string }, TaskMeta>(
      async () => exportCustom(directory),
      { type: TaskType.EXPORT_ASSET, meta: { title: t('actions.assets.export.task.title') } },
    );

    if (outcome.success) {
      // For web case (no directory selected), download the file using the returned file path
      if (!directory)
        await downloadCustomAssets(outcome.result.filePath);

      return { directory, filePath: outcome.result.filePath };
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      return { message: outcome.message, success: false };
    }

    return { message: '', success: false };
  };

  const restoreAssetsDatabase = async (resetType: 'hard' | 'soft'): Promise<ActionStatus> => {
    const outcome = await runTask<boolean, TaskMeta>(
      async () => restoreAssetsDatabaseCaller(resetType, resetType === 'hard'),
      { type: TaskType.RESET_ASSET, meta: { title: t('actions.assets.reset.task.title') } },
    );

    if (outcome.success) {
      return {
        success: true,
      };
    }

    if (isActionableFailure(outcome)) {
      logger.error(outcome.error);
      return { message: outcome.message, success: false };
    }

    return { message: '', success: false };
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

import type {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdatePayload,
  AssetUpdateResult,
} from '@/modules/assets/types';
import type { ActionStatus } from '@/modules/core/common/action';
import { isErr, map as mapResult, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage, useNotifications } from '@/modules/core/notifications/use-notifications';
import { isActionable, type TaskError } from '@/modules/core/tasks/task-result';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabel, activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

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
  const { submitTask } = useNativeTask();
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
    const outcome = await submitTask<AssetDBVersion>({
      id: makeActivityId(ActivityKind.ASSETS, ActivityPart.VERSIONS),
      kind: ActivityKind.ASSETS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<AssetDBVersion, TaskError>> => mapResult(
        await runTask<AssetDBVersion>(
          async () => checkForAssetUpdate(),
        ),
        result => result,
      ),
      subtitle: activityLabel(ActivityKind.ASSETS, ActivityPart.VERSIONS),
      title: t('task_center.group.assets'),
    });

    if (!isErr(outcome)) {
      const versions = outcome.value;
      return {
        updateAvailable: versions.local < versions.remote && versions.newChanges > 0,
        versions,
      };
    }
    if (isErr(outcome) && isActionable(outcome.error)) {
      const title = t('actions.assets.versions.task.title');
      const description = t('actions.assets.versions.error.description', {
        message: outcome.error.message,
      }).toString();

      notifyError(title, description);
    }
    return {
      updateAvailable: false,
    };
  };

  const applyUpdates = async ({ resolution, version }: AssetUpdatePayload): Promise<ApplyUpdateResult> => {
    const outcome = await submitTask<AssetUpdateResult>({
      id: makeActivityId(ActivityKind.ASSETS, ActivityPart.UPDATE),
      kind: ActivityKind.ASSETS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<AssetUpdateResult, TaskError>> => mapResult(
        await runTask<AssetUpdateResult>(
          async () => performUpdate(version, resolution),
        ),
        result => result,
      ),
      subtitle: activityLabel(ActivityKind.ASSETS, ActivityPart.UPDATE, { version }),
      title: t('task_center.group.assets'),
    });

    if (!isErr(outcome)) {
      const updateResult = outcome.value;
      if (typeof updateResult === 'boolean') {
        return {
          done: true,
        };
      }
      return {
        conflicts: updateResult,
        done: false,
      };
    }
    if (isActionable(outcome.error)) {
      const title = t('actions.assets.update.task.title');
      const description = t('actions.assets.update.error.description', {
        message: outcome.error.message,
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
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ASSETS, ActivityPart.IMPORT),
      kind: ActivityKind.ASSETS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => importCustom(path ?? file),
        ),
        () => {},
      ),
      subtitle: activityLabel(ActivityKind.ASSETS, ActivityPart.IMPORT, { file: file.name }),
      title: t('task_center.group.assets'),
    });

    if (!isErr(outcome))
      return { success: true };

    if (isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      return { message: outcome.error.message, success: false };
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

    const outcome = await submitTask<string>({
      id: makeActivityId(ActivityKind.ASSETS, ActivityPart.EXPORT),
      kind: ActivityKind.ASSETS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<string, TaskError>> => mapResult(
        await runTask<{ filePath: string }>(
          async () => exportCustom(directory),
        ),
        result => result.filePath,
      ),
      subtitle: activityLabel(ActivityKind.ASSETS, ActivityPart.EXPORT),
      title: t('task_center.group.assets'),
    });

    if (!isErr(outcome)) {
      const filePath = outcome.value;
      if (!appSession)
        await downloadCustomAssets(filePath);

      return { directory, filePath };
    }

    if (isErr(outcome) && isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      return { message: outcome.error.message, success: false };
    }

    return { message: '', success: false };
  };

  const restoreAssetsDatabase = async (resetType: 'hard' | 'soft'): Promise<ActionStatus> => {
    const outcome = await submitTask({
      id: makeActivityId(ActivityKind.ASSETS, ActivityPart.RESET),
      kind: ActivityKind.ASSETS,
      rerunnable: false,
      run: async ({ runTask }): Promise<Result<void, TaskError>> => mapResult(
        await runTask<boolean>(
          async () => restoreAssetsDatabaseCaller(resetType, resetType === 'hard'),
        ),
        () => {},
      ),
      subtitle: activityLabelFor(resetType === 'hard'
        ? msg.$t('task_center.activity.assets.reset_hard')
        : msg.$t('task_center.activity.assets.reset_soft')),
      title: t('task_center.group.assets'),
    });

    if (!isErr(outcome))
      return { success: true };

    if (isActionable(outcome.error)) {
      logger.error(outcome.error.message);
      return { message: outcome.error.message, success: false };
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

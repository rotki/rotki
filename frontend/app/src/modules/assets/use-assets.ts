import type { ActionStatus } from '@/modules/core/common/action';
import { err, isErr, map as mapResult, ok, type Result } from 'plainfp/result';
import { msg } from '@/message-key';
import { useAssetsApi } from '@/modules/assets/api/use-assets-api';
import {
  ApplyUpdateKind,
  type ApplyUpdateResult,
  type AssetDBVersion,
  type AssetMergePayload,
  type AssetUpdateCheckResult,
  type AssetUpdatePayload,
  type AssetUpdateResult,
} from '@/modules/assets/types';
import { ApiValidationError, type ValidationErrors } from '@/modules/core/api/types/errors';
import { logger } from '@/modules/core/common/logging/logging';
import { getErrorMessage } from '@/modules/core/notifications/use-notifications';
import { isActionable, onActionableError, type TaskError, TaskFailed } from '@/modules/core/tasks/task-result';
import { useInterop } from '@/modules/shell/app/use-electron-interop';
import { activityLabel, activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId } from '@/modules/task-center/core/types';
import { useNativeTask } from '@/modules/task-center/use-native-task';

interface ExportCustomAssetsResult {
  directory?: string;
  filePath: string;
}

interface UseAssetsReturn {
  /** Fails when the check did not finish (failed or cancelled), so a caller never reads that as "up to date". */
  checkForUpdate: () => Promise<Result<AssetUpdateCheckResult, TaskError>>;
  /**
   * Fails when the update did not finish, carrying the reason. The caller reports it, since only
   * the caller knows whether the user has a surface to read it on.
   */
  applyUpdates: (payload: AssetUpdatePayload) => Promise<Result<ApplyUpdateResult, TaskError>>;
  mergeAssets: (payload: AssetMergePayload) => Promise<ActionStatus<string | ValidationErrors>>;
  importCustomAssets: (file: File) => Promise<ActionStatus>;
  /** Fails as not actionable when the export was cancelled, so a caller can stay quiet. */
  exportCustomAssets: () => Promise<Result<ExportCustomAssetsResult, TaskError>>;
  /** Fails as not actionable when the reset was cancelled, so a caller can stay quiet. */
  restoreAssetsDatabase: (resetType: 'hard' | 'soft') => Promise<Result<void, TaskError>>;
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

  const checkForUpdate = async (): Promise<Result<AssetUpdateCheckResult, TaskError>> => {
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

    if (isErr(outcome))
      return outcome;

    const versions = outcome.value;
    return ok({
      updateAvailable: versions.local < versions.remote && versions.newChanges > 0,
      versions,
    });
  };

  const applyUpdates = async ({ resolution, version }: AssetUpdatePayload): Promise<Result<ApplyUpdateResult, TaskError>> => {
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

    return mapResult(outcome, (updateResult): ApplyUpdateResult => typeof updateResult === 'boolean'
      ? { kind: ApplyUpdateKind.DONE }
      : { conflicts: updateResult, kind: ApplyUpdateKind.CONFLICTS });
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

  const exportCustomAssets = async (): Promise<Result<ExportCustomAssetsResult, TaskError>> => {
    let directory: string | undefined;
    if (appSession) {
      const selectedDirectory = await openDirectory(t('common.select_directory').toString());
      if (!selectedDirectory)
        return err(TaskFailed({ message: t('assets.backup.missing_directory') }));

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

    if (isErr(outcome)) {
      onActionableError(outcome, error => logger.error(error.message));
      return outcome;
    }

    const filePath = outcome.value;
    if (!appSession)
      await downloadCustomAssets(filePath);

    return ok({ directory, filePath });
  };

  const restoreAssetsDatabase = async (resetType: 'hard' | 'soft'): Promise<Result<void, TaskError>> => {
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

    onActionableError(outcome, error => logger.error(error.message));
    return outcome;
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

import { acceptHMRUpdate, defineStore } from 'pinia';
import { interop } from '@/electron-interop';
import i18n from '@/i18n';
import { AssetUpdatePayload } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetUpdateCheckResult,
  AssetUpdateResult
} from '@/types/assets';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useAssets = defineStore('assets', () => {
  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    const { awaitTask } = useTasks();
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await api.assets.checkForAssetUpdate();
      const { result } = await awaitTask<AssetDBVersion, TaskMeta>(
        taskId,
        taskType,
        {
          title: i18n.t('actions.assets.versions.task.title').toString(),
          numericKeys: []
        }
      );

      return {
        updateAvailable: result.local < result.remote,
        versions: result
      };
    } catch (e: any) {
      const title = i18n.t('actions.assets.versions.task.title').toString();
      const description = i18n
        .t('actions.assets.versions.error.description', { message: e.message })
        .toString();
      const { notify } = useNotifications();
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
      const { awaitTask } = useTasks();
      const { taskId } = await api.assets.performUpdate(version, resolution);
      const { result } = await awaitTask<AssetUpdateResult, TaskMeta>(
        taskId,
        TaskType.ASSET_UPDATE_PERFORM,
        {
          title: i18n.t('actions.assets.update.task.title').toString(),
          numericKeys: []
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
      const title = i18n.t('actions.assets.update.task.title').toString();
      const description = i18n
        .t('actions.assets.update.error.description', { message: e.message })
        .toString();
      const { notify } = useNotifications();
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
  }: AssetMergePayload): Promise<ActionStatus> => {
    try {
      const success = await api.assets.mergeAssets(
        sourceIdentifier,
        targetIdentifier
      );
      return {
        success
      };
    } catch (e: any) {
      return {
        success: false,
        message: e.message
      };
    }
  };

  const restoreCustomAssets = async (file: File): Promise<ActionStatus> => {
    const isLocal = interop.isPackaged && api.defaultBackend;
    const { message, result: success } = await api.assets.restoreCustom(
      file,
      !isLocal
    );
    return {
      success,
      message
    };
  };

  const backupCustomAssets = async (): Promise<ActionStatus> => {
    const isLocal = interop.isPackaged && api.defaultBackend;
    let file: string | undefined = undefined;
    if (isLocal) {
      const directory = await interop.openDirectory(
        i18n.t('profit_loss_report.select_directory').toString()
      );
      if (!directory) {
        return {
          success: false,
          message: i18n.t('assets.backup.missing_directory').toString()
        };
      }
      file = directory;
    }
    return await api.assets.backupCustom(file);
  };

  return {
    checkForUpdate,
    applyUpdates,
    mergeAssets,
    restoreCustomAssets,
    backupCustomAssets
  };
});

if (module.hot) {
  module.hot.accept(acceptHMRUpdate(useAssets, module.hot));
}

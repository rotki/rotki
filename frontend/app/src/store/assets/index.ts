import { interop } from '@/electron-interop';
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
  const { awaitTask } = useTasks();
  const { t } = useI18n();

  const checkForUpdate = async (): Promise<AssetUpdateCheckResult> => {
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await api.assets.checkForAssetUpdate();
      const { result } = await awaitTask<AssetDBVersion, TaskMeta>(
        taskId,
        taskType,
        {
          title: t('actions.assets.versions.task.title').toString(),
          numericKeys: []
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
      const { taskId } = await api.assets.performUpdate(version, resolution);
      const { result } = await awaitTask<AssetUpdateResult, TaskMeta>(
        taskId,
        TaskType.ASSET_UPDATE_PERFORM,
        {
          title: t('actions.assets.update.task.title').toString(),
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
      const title = t('actions.assets.update.task.title').toString();
      const description = t('actions.assets.update.error.description', {
        message: e.message
      }).toString();
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

  const importCustomAssets = async (file: File): Promise<ActionStatus> => {
    try {
      await api.assets.importCustom(file, !interop.appSession);
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
      if (interop.appSession) {
        const directory = await interop.openDirectory(
          t('profit_loss_report.select_directory').toString()
        );
        if (!directory) {
          return {
            success: false,
            message: t('assets.backup.missing_directory').toString()
          };
        }
        file = directory;
      }
      return await api.assets.exportCustom(file);
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
});

if (import.meta.hot) {
  import.meta.hot.accept(acceptHMRUpdate(useAssets, import.meta.hot));
}

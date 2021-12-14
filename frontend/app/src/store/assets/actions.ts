import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { AssetUpdatePayload } from '@/services/assets/types';
import { api } from '@/services/rotkehlchen-api';
import {
  ApplyUpdateResult,
  AssetDBVersion,
  AssetMergePayload,
  AssetState,
  AssetUpdateCheckResult,
  AssetUpdateResult
} from '@/store/assets/types';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus, RotkehlchenState } from '@/store/types';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const actions: ActionTree<AssetState, RotkehlchenState> = {
  async checkForUpdate(): Promise<AssetUpdateCheckResult> {
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
  },

  async applyUpdates(
    _,
    { version, resolution }: AssetUpdatePayload
  ): Promise<ApplyUpdateResult> {
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
  },

  async mergeAssets(
    _,
    { sourceIdentifier, targetIdentifier }: AssetMergePayload
  ): Promise<ActionStatus> {
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
  }
};

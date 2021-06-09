import { ActionTree } from 'vuex';
import i18n from '@/i18n';
import { createTask, taskCompletion, TaskMeta } from '@/model/task';
import { TaskType } from '@/model/task-type';
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
import { Severity } from '@/store/notifications/consts';
import { notify } from '@/store/notifications/utils';
import { ActionStatus, RotkehlchenState } from '@/store/types';

export const actions: ActionTree<AssetState, RotkehlchenState> = {
  async checkForUpdate({ commit }): Promise<AssetUpdateCheckResult> {
    try {
      const taskType = TaskType.ASSET_UPDATE;
      const { taskId } = await api.assets.checkForAssetUpdate();
      const task = createTask(taskId, taskType, {
        title: i18n.t('actions.assets.versions.task.title').toString(),
        ignoreResult: false,
        numericKeys: []
      });

      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<AssetDBVersion, TaskMeta>(
        taskType
      );
      return {
        updateAvailable: result.local < result.remote,
        versions: result
      };
    } catch (e) {
      const title = i18n.t('actions.assets.versions.task.title').toString();
      const description = i18n
        .t('actions.assets.versions.error.description', { message: e.message })
        .toString();
      notify(description, title, Severity.ERROR, true);
      return {
        updateAvailable: false
      };
    }
  },

  async applyUpdates(
    { commit },
    { version, resolution }: AssetUpdatePayload
  ): Promise<ApplyUpdateResult> {
    try {
      const taskType = TaskType.ASSET_UPDATE_PERFORM;
      const { taskId } = await api.assets.performUpdate(version, resolution);
      const task = createTask(taskId, taskType, {
        title: i18n.t('actions.assets.update.task.title').toString(),
        ignoreResult: false,
        numericKeys: []
      });

      commit('tasks/add', task, { root: true });
      const { result } = await taskCompletion<AssetUpdateResult, TaskMeta>(
        taskType
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
    } catch (e) {
      const title = i18n.t('actions.assets.update.task.title').toString();
      const description = i18n
        .t('actions.assets.update.error.description', { message: e.message })
        .toString();
      notify(description, title, Severity.ERROR, true);
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
    } catch (e) {
      return {
        success: false,
        message: e.message
      };
    }
  }
};

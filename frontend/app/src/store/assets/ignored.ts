import { MaybeRef } from '@vueuse/core';
import { api } from '@/services/rotkehlchen-api';
import { useMessageStore } from '@/store/message';
import { useNotifications } from '@/store/notifications';
import { useTasks } from '@/store/tasks';
import { ActionStatus } from '@/store/types';
import { TaskMeta } from '@/types/task';
import { TaskType } from '@/types/task-type';

export const useIgnoredAssetsStore = defineStore('ignoredAssets', () => {
  const ignoredAssets = ref<string[]>([]);
  const { notify } = useNotifications();
  const { setMessage } = useMessageStore();
  const { t, tc } = useI18n();

  const fetchIgnoredAssets = async (): Promise<void> => {
    try {
      const ignored = await api.assets.ignoredAssets();
      set(ignoredAssets, ignored);
    } catch (e: any) {
      const title = tc('actions.session.ignored_assets.error.title');
      const message = tc('actions.session.ignored_assets.error.message', 0, {
        error: e.message
      });
      notify({
        title,
        message,
        display: true
      });
    }
  };

  const ignoreAsset = async (
    assets: string[] | string
  ): Promise<ActionStatus> => {
    try {
      const ignored = await api.assets.modifyAsset(
        true,
        Array.isArray(assets) ? assets : [assets]
      );
      set(ignoredAssets, ignored);
      return { success: true };
    } catch (e: any) {
      notify({
        title: t('ignore.failed.ignore_title').toString(),
        message: t('ignore.failed.ignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message: e.message
        }).toString(),
        display: true
      });
      return { success: false, message: e.message };
    }
  };

  const unignoreAsset = async (
    assets: string[] | string
  ): Promise<ActionStatus> => {
    try {
      const ignored = await api.assets.modifyAsset(
        false,
        Array.isArray(assets) ? assets : [assets]
      );
      set(ignoredAssets, ignored);
      return { success: true };
    } catch (e: any) {
      notify({
        title: t('ignore.failed.unignore_title').toString(),
        message: t('ignore.failed.unignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message: e.message
        }).toString(),
        display: true
      });
      return { success: false, message: e.message };
    }
  };

  const updateIgnoredAssets = async (): Promise<void> => {
    const { awaitTask } = useTasks();

    try {
      const taskType = TaskType.UPDATE_IGNORED_ASSETS;
      const { taskId } = await api.assets.updateIgnoredAssets();
      const taskMeta = {
        title: t('actions.session.update_ignored_assets.task.title').toString(),
        numericKeys: []
      };

      const { result } = await awaitTask<number, TaskMeta>(
        taskId,
        taskType,
        taskMeta
      );

      const title = t(
        'actions.session.update_ignored_assets.success.title'
      ).toString();
      const message =
        result > 0
          ? t('actions.session.update_ignored_assets.success.message', {
              total: result
            }).toString()
          : t('actions.session.update_ignored_assets.success.empty_message', {
              total: result
            }).toString();

      setMessage({
        title,
        description: message,
        success: true
      });
      await fetchIgnoredAssets();
    } catch (e: any) {
      const title = tc('actions.session.update_ignored_assets.error.title');
      const message = tc(
        'actions.session.update_ignored_assets.error.message',
        0,
        {
          error: e.message
        }
      );
      const { notify } = useNotifications();
      notify({
        title,
        message,
        display: true
      });
    }
  };

  const isAssetIgnored = (asset: MaybeRef<string>) =>
    computed<boolean>(() => {
      const selectedAsset = get(asset);
      return get(ignoredAssets).includes(selectedAsset);
    });

  return {
    ignoredAssets,
    fetchIgnoredAssets,
    ignoreAsset,
    unignoreAsset,
    updateIgnoredAssets,
    isAssetIgnored
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot)
  );
}

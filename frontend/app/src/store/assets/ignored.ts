import { type MaybeRef } from '@vueuse/core';
import { type ActionStatus } from '@/types/action';

export const useIgnoredAssetsStore = defineStore('assets/ignored', () => {
  const ignoredAssets = ref<string[]>([]);
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { getIgnoredAssets, addIgnoredAssets, removeIgnoredAssets } =
    useAssetIgnoreApi();

  const fetchIgnoredAssets = async (): Promise<void> => {
    try {
      const ignored = await getIgnoredAssets();
      set(ignoredAssets, ignored);
    } catch (e: any) {
      const title = t('actions.session.ignored_assets.error.title');
      const message = t('actions.session.ignored_assets.error.message', {
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
      const ignored = await addIgnoredAssets(
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
      const ignored = await removeIgnoredAssets(
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
    isAssetIgnored
  };
});

if (import.meta.hot) {
  import.meta.hot.accept(
    acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot)
  );
}

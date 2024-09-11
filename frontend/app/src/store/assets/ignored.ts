import type { MaybeRef } from '@vueuse/core';
import type { ActionStatus } from '@/types/action';

export const useIgnoredAssetsStore = defineStore('assets/ignored', () => {
  const ignoredAssets = ref<string[]>([]);
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { getIgnoredAssets, addIgnoredAssets, removeIgnoredAssets } = useAssetIgnoreApi();

  const fetchIgnoredAssets = async (): Promise<void> => {
    try {
      const ignored = await getIgnoredAssets();
      set(ignoredAssets, ignored);
    }
    catch (error: any) {
      const title = t('actions.session.ignored_assets.error.title');
      const message = t('actions.session.ignored_assets.error.message', {
        error: error.message,
      });
      notify({
        title,
        message,
        display: true,
      });
    }
  };

  const ignoreAsset = async (assets: string[] | string): Promise<ActionStatus> => {
    try {
      const { successful, noAction } = await addIgnoredAssets(arrayify(assets));
      set(ignoredAssets, [...get(ignoredAssets), ...successful, ...noAction].filter(uniqueStrings));
      return { success: true };
    }
    catch (error: any) {
      notify({
        title: t('ignore.failed.ignore_title').toString(),
        message: t('ignore.failed.ignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message: error.message,
        }).toString(),
        display: true,
      });
      return { success: false, message: error.message };
    }
  };

  const unignoreAsset = async (assets: string[] | string): Promise<ActionStatus> => {
    try {
      const { successful, noAction } = await removeIgnoredAssets(arrayify(assets));
      set(
        ignoredAssets,
        get(ignoredAssets).filter(asset => ![...successful, ...noAction].includes(asset)),
      );
      return { success: true };
    }
    catch (error: any) {
      notify({
        title: t('ignore.failed.unignore_title').toString(),
        message: t('ignore.failed.unignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message: error.message,
        }).toString(),
        display: true,
      });
      return { success: false, message: error.message };
    }
  };

  const isAssetIgnored = (asset: MaybeRef<string>): ComputedRef<boolean> => computed<boolean>(() => {
    const selectedAsset = get(asset);
    return get(ignoredAssets).includes(selectedAsset);
  });

  const addIgnoredAsset = (asset: string): void => {
    const ignored = get(ignoredAssets);
    if (!ignored.includes(asset))
      set(ignoredAssets, [...ignored, asset]);
  };

  return {
    ignoredAssets,
    fetchIgnoredAssets,
    ignoreAsset,
    unignoreAsset,
    isAssetIgnored,
    addIgnoredAsset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot));

import { uniqueStrings } from '@/utils/data';
import { arrayify } from '@/utils/array';
import { useNotificationsStore } from '@/store/notifications';
import type { MaybeRef } from '@vueuse/core';
import type { ActionStatus } from '@/types/action';

export const useIgnoredAssetsStore = defineStore('assets/ignored', () => {
  const ignoredAssets = ref<string[]>([]);
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { addIgnoredAssets, getIgnoredAssets, removeIgnoredAssets } = useAssetIgnoreApi();

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
        display: true,
        message,
        title,
      });
    }
  };

  const ignoreAsset = async (assets: string[] | string): Promise<ActionStatus> => {
    try {
      const { noAction, successful } = await addIgnoredAssets(arrayify(assets));
      set(ignoredAssets, [...get(ignoredAssets), ...successful, ...noAction].filter(uniqueStrings));
      return { success: true };
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('ignore.failed.ignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message: error.message,
        }),
        title: t('ignore.failed.ignore_title'),
      });
      return { message: error.message, success: false };
    }
  };

  const unignoreAsset = async (assets: string[] | string): Promise<ActionStatus> => {
    try {
      const { noAction, successful } = await removeIgnoredAssets(arrayify(assets));
      set(
        ignoredAssets,
        get(ignoredAssets).filter(asset => ![...successful, ...noAction].includes(asset)),
      );
      return { success: true };
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('ignore.failed.unignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message: error.message,
        }),
        title: t('ignore.failed.unignore_title'),
      });
      return { message: error.message, success: false };
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
    addIgnoredAsset,
    fetchIgnoredAssets,
    ignoreAsset,
    ignoredAssets,
    isAssetIgnored,
    unignoreAsset,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot));

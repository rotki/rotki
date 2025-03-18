import type { ActionStatus } from '@/types/action';
import type { MaybeRef } from '@vueuse/core';
import { useAssetIgnoreApi } from '@/composables/api/assets/ignore';
import { useConfirmStore } from '@/store/confirm';
import { useNotificationsStore } from '@/store/notifications';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';

export const useIgnoredAssetsStore = defineStore('assets/ignored', () => {
  const ignoredAssets = ref<string[]>([]);
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const { addIgnoredAssets, getIgnoredAssets, removeIgnoredAssets } = useAssetIgnoreApi();
  const { show } = useConfirmStore();

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

  const ignoreAssetWithConfirmation = async (assets: string[] | string, assetName?: string | null, onSuccess?: () => any): Promise<void> => {
    show({
      message: t('ignore.confirm.message', {
        asset: assetName || (typeof assets === 'string' ? assets : t('ignore.confirm.these_assets')),
      }),
      title: t('ignore.confirm.title'),
      type: 'warning',
    }, async () => {
      const { success } = await ignoreAsset(assets);
      if (success) {
        onSuccess?.();
      }
    });
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

  const useIsAssetIgnored = (asset: MaybeRef<string>): ComputedRef<boolean> => computed<boolean>(() => {
    const selectedAsset = get(asset);
    return get(ignoredAssets).includes(selectedAsset);
  });

  const isAssetIgnored = (asset: string): boolean => get(ignoredAssets).includes(asset);

  const addIgnoredAsset = (asset: string): void => {
    const ignored = get(ignoredAssets);
    if (!ignored.includes(asset))
      set(ignoredAssets, [...ignored, asset]);
  };

  return {
    addIgnoredAsset,
    fetchIgnoredAssets,
    ignoreAsset,
    ignoreAssetWithConfirmation,
    ignoredAssets,
    isAssetIgnored,
    unignoreAsset,
    useIsAssetIgnored,
  };
});

if (import.meta.hot)
  import.meta.hot.accept(acceptHMRUpdate(useIgnoredAssetsStore, import.meta.hot));

import type { ActionStatus } from '@/types/action';
import type { MaybeRef } from '@vueuse/core';
import { useAssetWhitelistApi } from '@/composables/api/assets/whitelist';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useNotificationsStore } from '@/store/notifications';

export const useWhitelistedAssetsStore = defineStore('assets/whitelisted', () => {
  const whitelistedAssets = ref<string[]>([]);
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const { addAssetToWhitelist, getWhitelistedAssets, removeAssetFromWhitelist } = useAssetWhitelistApi();

  const { fetchIgnoredAssets } = useIgnoredAssetsStore();

  const fetchWhitelistedAssets = async (): Promise<void> => {
    try {
      const whitelisted = await getWhitelistedAssets();
      set(whitelistedAssets, whitelisted);
    }
    catch (error: any) {
      const title = t('actions.session.whitelisted_assets.error.title');
      const message = t('actions.session.whitelisted_assets.error.message', {
        error: error.message,
      });
      notify({
        display: true,
        message,
        title,
      });
    }
  };

  const whitelistAsset = async (token: string): Promise<ActionStatus> => {
    try {
      await addAssetToWhitelist(token);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('ignore.whitelist.failed.whitelist_message', {
          message: error.message,
        }),
        title: t('ignore.whitelist.failed.whitelist_title'),
      });
      return { message: error.message, success: false };
    }
  };

  const unWhitelistAsset = async (token: string): Promise<ActionStatus> => {
    try {
      await removeAssetFromWhitelist(token);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('ignore.whitelist.failed.unwhitelist_message', {
          message: error.message,
        }),
        title: t('ignore.whitelist.failed.unwhitelist_title'),
      });
      return { message: error.message, success: false };
    }
  };

  const isAssetWhitelisted = (asset: MaybeRef<string>): ComputedRef<boolean> => computed<boolean>(() => {
    const selectedAsset = get(asset);
    return get(whitelistedAssets).includes(selectedAsset);
  });

  return {
    fetchWhitelistedAssets,
    isAssetWhitelisted,
    unWhitelistAsset,
    whitelistAsset,
    whitelistedAssets,
  };
});

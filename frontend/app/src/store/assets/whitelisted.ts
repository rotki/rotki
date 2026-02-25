import type { MaybeRef } from 'vue';
import type { ActionStatus } from '@/types/action';
import { useAssetWhitelistApi } from '@/composables/api/assets/whitelist';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { getErrorMessage } from '@/utils/error-handling';

export const useWhitelistedAssetsStore = defineStore('assets/whitelisted', () => {
  const whitelistedAssets = ref<string[]>([]);
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const { addAssetToWhitelist, getWhitelistedAssets, removeAssetFromWhitelist } = useAssetWhitelistApi();

  const { fetchIgnoredAssets } = useIgnoredAssetsStore();

  const fetchWhitelistedAssets = async (): Promise<void> => {
    try {
      const whitelisted = await getWhitelistedAssets();
      set(whitelistedAssets, whitelisted);
    }
    catch (error: unknown) {
      notifyError(
        t('actions.session.whitelisted_assets.error.title'),
        t('actions.session.whitelisted_assets.error.message', {
          error: getErrorMessage(error),
        }),
      );
    }
  };

  const whitelistAsset = async (token: string): Promise<ActionStatus> => {
    try {
      await addAssetToWhitelist(token);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      notifyError(
        t('ignore.whitelist.failed.whitelist_title'),
        t('ignore.whitelist.failed.whitelist_message', {
          message,
        }),
      );
      return { message, success: false };
    }
  };

  const unWhitelistAsset = async (token: string): Promise<ActionStatus> => {
    try {
      await removeAssetFromWhitelist(token);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      notifyError(
        t('ignore.whitelist.failed.unwhitelist_title'),
        t('ignore.whitelist.failed.unwhitelist_message', {
          message,
        }),
      );
      return { message, success: false };
    }
  };

  const isAssetWhitelisted = (asset: string): boolean => get(whitelistedAssets).includes(asset);

  const useIsAssetWhitelisted = (asset: MaybeRef<string>): ComputedRef<boolean> => computed<boolean>(() => {
    const selectedAsset = get(asset);
    return isAssetWhitelisted(selectedAsset);
  });

  return {
    fetchWhitelistedAssets,
    isAssetWhitelisted,
    unWhitelistAsset,
    useIsAssetWhitelisted,
    whitelistAsset,
    whitelistedAssets,
  };
});

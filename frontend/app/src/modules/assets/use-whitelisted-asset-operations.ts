import type { ActionStatus } from '@/modules/core/common/action';
import { useAssetWhitelistApi } from '@/modules/assets/api/use-asset-whitelist-api';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { getErrorMessage } from '@/modules/core/common/logging/error-handling';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseWhitelistedAssetOperationsReturn {
  fetchWhitelistedAssets: () => Promise<void>;
  whitelistAsset: (token: string) => Promise<ActionStatus>;
  unWhitelistAsset: (token: string) => Promise<ActionStatus>;
}

export function useWhitelistedAssetOperations(): UseWhitelistedAssetOperationsReturn {
  const { notifyError } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { addAssetToWhitelist, getWhitelistedAssets, removeAssetFromWhitelist } = useAssetWhitelistApi();
  const { fetchIgnoredAssets } = useIgnoredAssetOperations();
  const { whitelistedAssets } = storeToRefs(useAssetsStore());

  async function fetchWhitelistedAssets(): Promise<void> {
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
  }

  async function whitelistAsset(token: string): Promise<ActionStatus> {
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
  }

  async function unWhitelistAsset(token: string): Promise<ActionStatus> {
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
  }

  return {
    fetchWhitelistedAssets,
    unWhitelistAsset,
    whitelistAsset,
  };
}

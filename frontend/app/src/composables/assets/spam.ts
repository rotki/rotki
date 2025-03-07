import type { ActionStatus } from '@/types/action';
import { useAssetSpamApi } from '@/composables/api/assets/spam';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { useNotificationsStore } from '@/store/notifications';

interface UseSpamAssetReturn {
  markAssetsAsSpam: (tokens: string[]) => Promise<ActionStatus>;
  removeAssetFromSpamList: (token: string) => Promise<ActionStatus>;
}

export function useSpamAsset(): UseSpamAssetReturn {
  const { notify } = useNotificationsStore();
  const { t } = useI18n();

  const {
    markAssetsAsSpam: markAssetAsSpamCaller,
    removeAssetFromSpamList: removeAssetFromSpamListCaller,
  } = useAssetSpamApi();

  const { fetchWhitelistedAssets } = useWhitelistedAssetsStore();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();

  const markAssetsAsSpam = async (tokens: string[]): Promise<ActionStatus> => {
    try {
      await markAssetAsSpamCaller(tokens);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('ignore.spam.failed.mark_message', {
          message: error.message,
        }),
        title: t('ignore.spam.failed.mark_title'),
      });
      return { message: error.message, success: false };
    }
  };

  const removeAssetFromSpamList = async (token: string): Promise<ActionStatus> => {
    try {
      await removeAssetFromSpamListCaller(token);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: any) {
      notify({
        display: true,
        message: t('ignore.spam.failed.unmark_message', {
          message: error.message,
        }),
        title: t('ignore.spam.failed.unmark_title'),
      });
      return { message: error.message, success: false };
    }
  };

  return {
    markAssetsAsSpam,
    removeAssetFromSpamList,
  };
}

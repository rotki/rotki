import type { ActionStatus } from '@/types/action';

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
        title: t('ignore.spam.failed.mark_title'),
        message: t('ignore.spam.failed.mark_message', {
          message: error.message,
        }),
        display: true,
      });
      return { success: false, message: error.message };
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
        title: t('ignore.spam.failed.unmark_title'),
        message: t('ignore.spam.failed.unmark_message', {
          message: error.message,
        }),
        display: true,
      });
      return { success: false, message: error.message };
    }
  };

  return {
    markAssetsAsSpam,
    removeAssetFromSpamList,
  };
}

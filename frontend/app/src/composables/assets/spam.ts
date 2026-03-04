import type { ActionStatus } from '@/types/action';
import { useAssetSpamApi } from '@/composables/api/assets/spam';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { getErrorMessage } from '@/utils/error-handling';

interface UseSpamAssetReturn {
  markAssetsAsSpam: (tokens: string[]) => Promise<ActionStatus>;
  removeAssetFromSpamList: (token: string) => Promise<ActionStatus>;
}

export function useSpamAsset(): UseSpamAssetReturn {
  const { notifyError, showErrorMessage } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });

  const {
    markAssetsAsSpam: markAssetAsSpamCaller,
    removeAssetFromSpamList: removeAssetFromSpamListCaller,
  } = useAssetSpamApi();

  const { fetchWhitelistedAssets } = useWhitelistedAssetsStore();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();

  const { getAssetField } = useAssetInfoRetrieval();
  const { manualBalancesAssets } = useManualBalanceData();
  const markAssetsAsSpam = async (tokens: string[]): Promise<ActionStatus> => {
    try {
      const includedInManualBalances: string[] = [];
      const notIncludedInManualBalances: string[] = [];

      for (const asset of tokens) {
        if (get(manualBalancesAssets).includes(asset)) {
          includedInManualBalances.push(asset);
        }
        else {
          notIncludedInManualBalances.push(asset);
        }
      }

      // Display a warning message if any assets are included in manual balances
      if (includedInManualBalances.length > 0) {
        showErrorMessage(
          t('ignore.spam.warning.manual_balances_title'),
          t('ignore.spam.warning.manual_balances_message', {
            assets: includedInManualBalances.map(item => getAssetField(item, 'symbol')).join(', '),
          }),
        );
      }

      if (notIncludedInManualBalances.length > 0) {
        await markAssetAsSpamCaller(tokens);
        await fetchWhitelistedAssets();
        await fetchIgnoredAssets();
      }

      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      notifyError(
        t('ignore.spam.failed.mark_title'),
        t('ignore.spam.failed.mark_message', {
          message,
        }),
      );
      return { message, success: false };
    }
  };

  const removeAssetFromSpamList = async (token: string): Promise<ActionStatus> => {
    try {
      await removeAssetFromSpamListCaller(token);
      await fetchWhitelistedAssets();
      await fetchIgnoredAssets();
      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      notifyError(
        t('ignore.spam.failed.unmark_title'),
        t('ignore.spam.failed.unmark_message', {
          message,
        }),
      );
      return { message, success: false };
    }
  };

  return {
    markAssetsAsSpam,
    removeAssetFromSpamList,
  };
}

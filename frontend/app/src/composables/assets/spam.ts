import type { ActionStatus } from '@/types/action';
import { useAssetSpamApi } from '@/composables/api/assets/spam';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { useMessageStore } from '@/store/message';
import { useNotificationsStore } from '@/store/notifications';

interface UseSpamAssetReturn {
  markAssetsAsSpam: (tokens: string[]) => Promise<ActionStatus>;
  removeAssetFromSpamList: (token: string) => Promise<ActionStatus>;
}

export function useSpamAsset(): UseSpamAssetReturn {
  const { notify } = useNotificationsStore();
  const { t } = useI18n({ useScope: 'global' });

  const {
    markAssetsAsSpam: markAssetAsSpamCaller,
    removeAssetFromSpamList: removeAssetFromSpamListCaller,
  } = useAssetSpamApi();

  const { fetchWhitelistedAssets } = useWhitelistedAssetsStore();
  const { fetchIgnoredAssets } = useIgnoredAssetsStore();

  const { getAssetSymbol } = useAssetInfoRetrieval();
  const { manualBalancesAssets } = useManualBalanceData();
  const { setMessage } = useMessageStore();

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
        setMessage({
          description: t('ignore.spam.warning.manual_balances_message', {
            assets: includedInManualBalances.map(item => getAssetSymbol(item)).join(', '),
          }),
          title: t('ignore.spam.warning.manual_balances_title'),
        });
      }

      if (notIncludedInManualBalances.length > 0) {
        await markAssetAsSpamCaller(tokens);
        await fetchWhitelistedAssets();
        await fetchIgnoredAssets();
      }

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

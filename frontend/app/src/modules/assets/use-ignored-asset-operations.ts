import type { ActionStatus } from '@/modules/common/action';
import { useAssetIgnoreApi } from '@/composables/api/assets/ignore';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { arrayify } from '@/utils/array';
import { uniqueStrings } from '@/utils/data';
import { getErrorMessage } from '@/utils/error-handling';

interface UseIgnoredAssetOperationsReturn {
  fetchIgnoredAssets: () => Promise<void>;
  ignoreAsset: (assets: string[] | string) => Promise<ActionStatus>;
  unignoreAsset: (assets: string[] | string) => Promise<ActionStatus>;
}

export function useIgnoredAssetOperations(): UseIgnoredAssetOperationsReturn {
  const { notifyError, showErrorMessage } = useNotifications();
  const { t } = useI18n({ useScope: 'global' });
  const { addIgnoredAssets, getIgnoredAssets, removeIgnoredAssets } = useAssetIgnoreApi();
  const { getAssetField } = useAssetInfoRetrieval();
  const { manualBalancesAssets } = useManualBalanceData();
  const { ignoredAssets } = storeToRefs(useAssetsStore());

  async function fetchIgnoredAssets(): Promise<void> {
    try {
      const ignored = await getIgnoredAssets();
      set(ignoredAssets, ignored);
    }
    catch (error: unknown) {
      const title = t('actions.session.ignored_assets.error.title');
      const message = t('actions.session.ignored_assets.error.message', {
        error: getErrorMessage(error),
      });
      notifyError(title, message);
    }
  }

  async function ignoreAsset(assets: string[] | string): Promise<ActionStatus> {
    const assetsArray = arrayify(assets);
    try {
      const includedInManualBalances: string[] = [];
      const notIncludedInManualBalances: string[] = [];

      for (const asset of assetsArray) {
        if (get(manualBalancesAssets).includes(asset)) {
          includedInManualBalances.push(asset);
        }
        else {
          notIncludedInManualBalances.push(asset);
        }
      }

      if (includedInManualBalances.length > 0) {
        showErrorMessage(
          t('ignore.warning.manual_balances_title'),
          t('ignore.warning.manual_balances_message', {
            assets: includedInManualBalances.map(item => getAssetField(item, 'symbol')).join(', '),
          }),
        );
      }

      if (notIncludedInManualBalances.length > 0) {
        const { noAction, successful } = await addIgnoredAssets(notIncludedInManualBalances);
        set(ignoredAssets, [...get(ignoredAssets), ...successful, ...noAction].filter(uniqueStrings));
      }
      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      notifyError(
        t('ignore.failed.ignore_title'),
        t('ignore.failed.ignore_message', {
          length: assetsArray.length,
          message,
        }),
      );
      return { message, success: false };
    }
  }

  async function unignoreAsset(assets: string[] | string): Promise<ActionStatus> {
    try {
      const { noAction, successful } = await removeIgnoredAssets(arrayify(assets));
      set(
        ignoredAssets,
        get(ignoredAssets).filter(asset => ![...successful, ...noAction].includes(asset)),
      );
      return { success: true };
    }
    catch (error: unknown) {
      const message = getErrorMessage(error);
      notifyError(
        t('ignore.failed.unignore_title'),
        t('ignore.failed.unignore_message', {
          length: Array.isArray(assets) ? assets.length : 1,
          message,
        }),
      );
      return { message, success: false };
    }
  }

  return {
    fetchIgnoredAssets,
    ignoreAsset,
    unignoreAsset,
  };
}

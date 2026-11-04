import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { uniqueStrings } from '@/modules/core/common/data/data';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

interface UseSelectedAssetIgnoringReturn {
  ignoreSelected: (identifiers: string[], ignored: boolean) => Promise<boolean>;
}

interface UseSelectedAssetSpamReturn {
  markSelectedAsSpam: (identifiers: string[]) => Promise<boolean>;
}

/**
 * Bulk ignore and unignore for a table selection of asset identifiers.
 *
 * @remarks
 * Tells the user when there is nothing to act on instead of calling the backend with an empty list,
 * and resolves to whether the backend call succeeded, so the caller decides what to clear and
 * refresh afterwards.
 */
export function useSelectedAssetIgnoring(): UseSelectedAssetIgnoringReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const { isAssetIgnored } = useAssetsStore();
  const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();

  /**
   * Ignores (or unignores) the selected assets.
   *
   * @remarks
   * Assets already in the requested state are skipped, so a selection where every asset is already
   * ignored counts as empty.
   */
  async function ignoreSelected(identifiers: string[], ignored: boolean): Promise<boolean> {
    const ids = identifiers
      .filter(identifier => isAssetIgnored(identifier) !== ignored)
      .filter(uniqueStrings);

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      showErrorMessage(t('ignore.no_items.title', choice), t('ignore.no_items.description', choice));
      return false;
    }

    const status = ignored ? await ignoreAsset(ids) : await unignoreAsset(ids);
    return status.success;
  }

  return { ignoreSelected };
}

/**
 * Bulk mark-as-spam for a table selection of asset identifiers, with the same empty-selection
 * message and success result as {@link useSelectedAssetIgnoring}.
 */
export function useSelectedAssetSpam(): UseSelectedAssetSpamReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const { markAssetsAsSpam } = useSpamAsset();

  async function markSelectedAsSpam(identifiers: string[]): Promise<boolean> {
    const ids = identifiers.filter(uniqueStrings);

    if (ids.length === 0) {
      showErrorMessage(t('ignore.spam.no_items.title'), t('ignore.spam.no_items.description'));
      return false;
    }

    const status = await markAssetsAsSpam(ids);
    return status.success;
  }

  return { markSelectedAsSpam };
}

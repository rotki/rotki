import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface UseIgnoredAssetConfirmationReturn {
  ignoreAssetWithConfirmation: (assets: string[] | string, assetName?: string | null, onSuccess?: () => any) => Promise<void>;
}

export function useIgnoredAssetConfirmation(): UseIgnoredAssetConfirmationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { ask } = useConfirmStore();
  const { ignoreAsset } = useIgnoredAssetOperations();

  /** Asks, then ignores; settles only once the ignore itself has, so a caller's loading flag spans it. */
  async function ignoreAssetWithConfirmation(assets: string[] | string, assetName?: string | null, onSuccess?: () => any): Promise<void> {
    const choice = await ask({
      message: t('ignore.confirm.message', {
        asset: assetName ?? (typeof assets === 'string' ? assets : t('ignore.confirm.these_assets')),
      }),
      title: t('ignore.confirm.title'),
      type: 'warning',
    });
    if (choice !== 'confirm')
      return;

    const { success } = await ignoreAsset(assets);
    if (success)
      onSuccess?.();
  }

  return {
    ignoreAssetWithConfirmation,
  };
}

import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useConfirmStore } from '@/modules/core/common/use-confirm-store';

interface UseIgnoredAssetConfirmationReturn {
  ignoreAssetWithConfirmation: (assets: string[] | string, assetName?: string | null, onSuccess?: () => any) => Promise<void>;
}

export function useIgnoredAssetConfirmation(): UseIgnoredAssetConfirmationReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { show } = useConfirmStore();
  const { ignoreAsset } = useIgnoredAssetOperations();

  async function ignoreAssetWithConfirmation(assets: string[] | string, assetName?: string | null, onSuccess?: () => any): Promise<void> {
    show({
      message: t('ignore.confirm.message', {
        asset: assetName || (typeof assets === 'string' ? assets : t('ignore.confirm.these_assets')),
      }),
      title: t('ignore.confirm.title'),
      type: 'warning',
    }, async () => {
      const { success } = await ignoreAsset(assets);
      if (success) {
        onSuccess?.();
      }
    });
  }

  return {
    ignoreAssetWithConfirmation,
  };
}

import type { MaybeRefOrGetter, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { startPromise } from '@shared/utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetConfirmation } from '@/modules/assets/use-ignored-asset-confirmation';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useSelectedAssetIgnoring } from '@/modules/assets/use-selected-asset-actions';

interface UseNftAssetIgnoringReturn {
  modelSelected: Ref<string[]>;
  massIgnore: (ignored: boolean) => Promise<void>;
  refreshCallback: () => void;
  toggleIgnoreAsset: (balance: NonFungibleBalance) => Promise<void>;
}

export function useNftAssetIgnoring(
  fetchData: () => Promise<void>,
  ignoredAssetsHandling: MaybeRefOrGetter<IgnoredAssetsHandlingType>,
): UseNftAssetIgnoringReturn {
  const { ignoreAssetWithConfirmation } = useIgnoredAssetConfirmation();
  const { unignoreAsset } = useIgnoredAssetOperations();
  const { ignoreSelected } = useSelectedAssetIgnoring();
  const { isAssetIgnored } = useAssetsStore();

  const modelSelected = ref<string[]>([]);

  function refreshCallback(): void {
    if (toValue(ignoredAssetsHandling) !== 'none') {
      startPromise(fetchData());
    }
  }

  async function toggleIgnoreAsset(balance: NonFungibleBalance): Promise<void> {
    const { id, name } = balance;
    if (isAssetIgnored(id)) {
      const response = await unignoreAsset(id);
      if (response.success) {
        refreshCallback();
      }
    }
    else {
      await ignoreAssetWithConfirmation(id, name, refreshCallback);
    }
  }

  async function massIgnore(ignored: boolean): Promise<void> {
    if (await ignoreSelected(get(modelSelected), ignored)) {
      set(modelSelected, []);
      if (toValue(ignoredAssetsHandling) !== 'none')
        await fetchData();
    }
  }

  return {
    massIgnore,
    refreshCallback,
    modelSelected,
    toggleIgnoreAsset,
  };
}

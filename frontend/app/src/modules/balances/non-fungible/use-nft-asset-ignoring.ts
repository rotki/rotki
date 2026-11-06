import type { MaybeRefOrGetter, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import type { NonFungibleBalance } from '@/modules/balances/types/nfbalances';
import { startPromise } from '@shared/utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
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
  const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
  const { ignoreSelected } = useSelectedAssetIgnoring();
  const { isAssetIgnored } = useAssetsStore();

  const modelSelected = ref<string[]>([]);

  function refreshCallback(): void {
    if (toValue(ignoredAssetsHandling) !== 'none') {
      startPromise(fetchData());
    }
  }

  async function toggleIgnoreAsset(balance: NonFungibleBalance): Promise<void> {
    const { id } = balance;
    const response = isAssetIgnored(id) ? await unignoreAsset(id) : await ignoreAsset(id);
    if (response.success)
      refreshCallback();
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

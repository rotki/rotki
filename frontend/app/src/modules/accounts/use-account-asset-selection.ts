import type { DeepReadonly, Ref } from 'vue';
import { get } from '@vueuse/core';
import { useSelectedAssetActions } from '@/modules/assets/use-selected-asset-actions';

interface UseAccountAssetSelectionReturn {
  handleIgnoreSelected: (ignored: boolean) => Promise<void>;
  handleMarkSelectedAsSpam: () => Promise<void>;
  selectedAssets: Ref<string[] | undefined>;
  selectionMode: DeepReadonly<Ref<boolean>>;
  toggleSelectionMode: () => void;
}

export function useAccountAssetSelection(
  onRefresh: () => Promise<void>,
): UseAccountAssetSelectionReturn {
  const selectionMode = shallowRef<boolean>(false);
  const selectedAssets = ref<string[]>([]);

  const { ignoreSelected, markSelectedAsSpam } = useSelectedAssetActions();

  function toggleSelectionMode(): void {
    set(selectionMode, !get(selectionMode));
    if (!get(selectionMode))
      set(selectedAssets, []);
  }

  async function finishSelection(): Promise<void> {
    set(selectedAssets, []);
    await onRefresh();
    toggleSelectionMode();
  }

  async function handleIgnoreSelected(ignored: boolean): Promise<void> {
    if (await ignoreSelected(get(selectedAssets), ignored))
      await finishSelection();
  }

  async function handleMarkSelectedAsSpam(): Promise<void> {
    if (await markSelectedAsSpam(get(selectedAssets)))
      await finishSelection();
  }

  const computedSelectedAssets = computed<string[] | undefined>({
    get() {
      if (!get(selectionMode)) {
        return undefined;
      }
      return get(selectedAssets);
    },
    set(value: string[] | undefined) {
      set(selectedAssets, value);
    },
  });

  return {
    handleIgnoreSelected,
    handleMarkSelectedAsSpam,
    selectedAssets: computedSelectedAssets,
    selectionMode: readonly(selectionMode),
    toggleSelectionMode,
  };
}

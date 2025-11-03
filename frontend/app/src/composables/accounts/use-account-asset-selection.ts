import type { Ref } from 'vue';
import { get } from '@vueuse/core';
import { useSpamAsset } from '@/composables/assets/spam';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useMessageStore } from '@/store/message';

interface UseAccountAssetSelectionReturn {
  handleIgnoreSelected: (ignored: boolean) => Promise<void>;
  handleMarkSelectedAsSpam: () => Promise<void>;
  selectedAssets: Ref<string[] | undefined>;
  selectionMode: Ref<boolean>;
  toggleSelectionMode: () => void;
}

export function useAccountAssetSelection(
  onRefresh: () => Promise<void>,
): UseAccountAssetSelectionReturn {
  const { t } = useI18n({ useScope: 'global' });

  const selectionMode = ref<boolean>(false);
  const selectedAssets = ref<string[]>([]);

  const { ignoreAsset, unignoreAsset } = useIgnoredAssetsStore();
  const { markAssetsAsSpam } = useSpamAsset();
  const { setMessage } = useMessageStore();

  function toggleSelectionMode(): void {
    set(selectionMode, !get(selectionMode));
    if (!get(selectionMode))
      set(selectedAssets, []);
  }

  async function handleIgnoreSelected(ignored: boolean): Promise<void> {
    const ids = get(selectedAssets);

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      setMessage({
        description: t('ignore.no_items.description', choice),
        success: false,
        title: t('ignore.no_items.title', choice),
      });
      return;
    }

    let status;
    if (ignored)
      status = await ignoreAsset(ids);
    else
      status = await unignoreAsset(ids);

    if (status.success) {
      set(selectedAssets, []);
      await onRefresh();
      toggleSelectionMode();
    }
  }

  async function handleMarkSelectedAsSpam(): Promise<void> {
    const ids = get(selectedAssets);

    if (ids.length === 0) {
      setMessage({
        description: t('ignore.spam.no_items.description'),
        success: false,
        title: t('ignore.spam.no_items.title'),
      });
      return;
    }

    const status = await markAssetsAsSpam(ids);

    if (status.success) {
      set(selectedAssets, []);
      await onRefresh();
      toggleSelectionMode();
    }
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
    selectionMode,
    toggleSelectionMode,
  };
}

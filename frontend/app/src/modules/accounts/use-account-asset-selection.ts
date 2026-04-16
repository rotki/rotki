import type { DeepReadonly, Ref } from 'vue';
import { get } from '@vueuse/core';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useNotifications } from '@/modules/core/notifications/use-notifications';

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
  const { t } = useI18n({ useScope: 'global' });

  const selectionMode = shallowRef<boolean>(false);
  const selectedAssets = ref<string[]>([]);

  const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
  const { markAssetsAsSpam } = useSpamAsset();
  const { showErrorMessage } = useNotifications();

  function toggleSelectionMode(): void {
    set(selectionMode, !get(selectionMode));
    if (!get(selectionMode))
      set(selectedAssets, []);
  }

  async function handleIgnoreSelected(ignored: boolean): Promise<void> {
    const ids = get(selectedAssets);

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      showErrorMessage(t('ignore.no_items.title', choice), t('ignore.no_items.description', choice));
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
      showErrorMessage(t('ignore.spam.no_items.title'), t('ignore.spam.no_items.description'));
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
    selectionMode: readonly(selectionMode),
    toggleSelectionMode,
  };
}

import type { MaybeRefOrGetter, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { NonFungibleBalance } from '@/types/nfbalances';
import { startPromise } from '@shared/utils';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetConfirmation } from '@/modules/assets/use-ignored-asset-confirmation';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { uniqueStrings } from '@/utils/data';

interface UseNftAssetIgnoringReturn {
  selected: Ref<string[]>;
  massIgnore: (ignored: boolean) => Promise<void>;
  refreshCallback: () => void;
  toggleIgnoreAsset: (balance: NonFungibleBalance) => Promise<void>;
}

export function useNftAssetIgnoring(
  fetchData: () => Promise<void>,
  ignoredAssetsHandling: MaybeRefOrGetter<IgnoredAssetsHandlingType>,
): UseNftAssetIgnoringReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { showErrorMessage } = useNotifications();
  const { ignoreAssetWithConfirmation } = useIgnoredAssetConfirmation();
  const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
  const { isAssetIgnored } = useAssetsStore();

  const selected = ref<string[]>([]);

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
    const ids = get(selected)
      .filter((item) => {
        const isItemIgnored = isAssetIgnored(item);
        return ignored ? !isItemIgnored : isItemIgnored;
      })
      .filter(uniqueStrings);

    let status: ActionStatus;

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      showErrorMessage(t('ignore.no_items.title', choice), t('ignore.no_items.description', choice));
      return;
    }

    if (ignored)
      status = await ignoreAsset(ids);
    else status = await unignoreAsset(ids);

    if (status.success) {
      set(selected, []);
      if (toValue(ignoredAssetsHandling) !== 'none')
        await fetchData();
    }
  }

  return {
    massIgnore,
    refreshCallback,
    selected,
    toggleIgnoreAsset,
  };
}

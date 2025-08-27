import type { Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import type { NonFungibleBalance } from '@/types/nfbalances';
import { startPromise } from '@shared/utils';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useMessageStore } from '@/store/message';
import { uniqueStrings } from '@/utils/data';

interface UseNftAssetIgnoringReturn {
  selected: Ref<string[]>;
  massIgnore: (ignored: boolean) => Promise<void>;
  refreshCallback: () => void;
  toggleIgnoreAsset: (balance: NonFungibleBalance) => Promise<void>;
}

export function useNftAssetIgnoring(
  fetchData: () => Promise<void>,
  ignoredAssetsHandling: Ref<IgnoredAssetsHandlingType>,
): UseNftAssetIgnoringReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { setMessage } = useMessageStore();
  const { ignoreAsset, ignoreAssetWithConfirmation, unignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();

  const selected = ref<string[]>([]);

  function refreshCallback(): void {
    if (get(ignoredAssetsHandling) !== 'none') {
      startPromise(fetchData());
    }
  }

  async function toggleIgnoreAsset(balance: NonFungibleBalance): Promise<void> {
    const { id, name } = balance;
    if (get(useIsAssetIgnored(id))) {
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
        const isItemIgnored = get(useIsAssetIgnored(item));
        return ignored ? !isItemIgnored : isItemIgnored;
      })
      .filter(uniqueStrings);

    let status: ActionStatus;

    if (ids.length === 0) {
      const choice = ignored ? 1 : 2;
      setMessage({
        description: t('ignore.no_items.description', choice),
        success: false,
        title: t('ignore.no_items.title', choice),
      });
      return;
    }

    if (ignored)
      status = await ignoreAsset(ids);
    else status = await unignoreAsset(ids);

    if (status.success) {
      set(selected, []);
      if (get(ignoredAssetsHandling) !== 'none')
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

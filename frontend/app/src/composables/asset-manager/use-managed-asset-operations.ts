import type { SupportedAsset } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSpamAsset } from '@/composables/assets/spam';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';
import { useMessageStore } from '@/store/message';
import { uniqueStrings } from '@/utils/data';

interface IgnoredFilter {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}

interface UseManagedAssetOperationsReturn {
  isAssetWhitelisted: (identifier: string) => ComputedRef<boolean>;
  isSpamAsset: (asset: SupportedAsset) => boolean;
  massIgnore: (ignored: boolean) => Promise<void>;
  massSpam: () => Promise<void>;
  toggleIgnoreAsset: (asset: SupportedAsset) => Promise<void>;
  toggleSpam: (item: SupportedAsset) => Promise<void>;
  toggleWhitelistAsset: (identifier: string) => Promise<void>;
  useIsAssetIgnored: (identifier: string) => ComputedRef<boolean>;
}

export function useManagedAssetOperations(
  onRefresh: () => void,
  ignoredFilter: Ref<IgnoredFilter>,
  selected: Ref<string[]>,
): UseManagedAssetOperationsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { setMessage } = useMessageStore();
  const { ignoreAsset, ignoreAssetWithConfirmation, unignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();
  const { isAssetWhitelisted, unWhitelistAsset, whitelistAsset } = useWhitelistedAssetsStore();
  const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();
  const { refetchAssetInfo } = useAssetInfoRetrieval();

  const isSpamAsset = (asset: SupportedAsset): boolean => asset.protocol === 'spam';

  function refreshAssetsConditionally(): void {
    if (get(ignoredFilter).ignoredAssetsHandling !== 'none')
      onRefresh();
  }

  const toggleIgnoreAsset = async (asset: SupportedAsset): Promise<void> => {
    const { identifier, name, symbol } = asset;
    if (get(useIsAssetIgnored(identifier))) {
      await unignoreAsset(identifier);
      refreshAssetsConditionally();
    }
    else {
      await ignoreAssetWithConfirmation(identifier, symbol || name, refreshAssetsConditionally);
    }
  };

  const toggleSpam = async (item: SupportedAsset): Promise<void> => {
    const { identifier } = item;
    if (isSpamAsset(item))
      await removeAssetFromSpamList(identifier);
    else
      await markAssetsAsSpam([identifier]);

    refetchAssetInfo(identifier);
    onRefresh();
  };

  const toggleWhitelistAsset = async (identifier: string): Promise<void> => {
    if (get(isAssetWhitelisted(identifier)))
      await unWhitelistAsset(identifier);
    else
      await whitelistAsset(identifier);

    onRefresh();
  };

  const massIgnore = async (ignored: boolean): Promise<void> => {
    const ids = get(selected)
      .filter((identifier) => {
        const isItemIgnored = get(useIsAssetIgnored(identifier));
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
    else
      status = await unignoreAsset(ids);

    if (status.success) {
      set(selected, []);
      if (get(ignoredFilter).ignoredAssetsHandling !== 'none')
        onRefresh();
    }
  };

  const massSpam = async (): Promise<void> => {
    const ids = get(selected).filter(uniqueStrings);

    if (ids.length === 0) {
      setMessage({
        description: t('ignore.spam.no_items.description'),
        success: false,
        title: t('ignore.spam.no_items.title'),
      });
      return;
    }

    const status: ActionStatus = await markAssetsAsSpam(ids);

    if (status.success) {
      set(selected, []);
      if (get(ignoredFilter).ignoredAssetsHandling !== 'none')
        onRefresh();
    }
  };

  return {
    isAssetWhitelisted,
    isSpamAsset,
    massIgnore,
    massSpam,
    toggleIgnoreAsset,
    toggleSpam,
    toggleWhitelistAsset,
    useIsAssetIgnored,
  };
}

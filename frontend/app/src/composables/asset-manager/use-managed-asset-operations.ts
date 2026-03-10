import type { SupportedAsset } from '@rotki/common';
import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import type { ActionStatus } from '@/types/action';
import type { IgnoredAssetsHandlingType } from '@/types/asset';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useSpamAsset } from '@/composables/assets/spam';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetConfirmation } from '@/modules/assets/use-ignored-asset-confirmation';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';
import { useNotifications } from '@/modules/notifications/use-notifications';
import { uniqueStrings } from '@/utils/data';

interface IgnoredFilter {
  onlyShowOwned: boolean;
  onlyShowWhitelisted: boolean;
  ignoredAssetsHandling: IgnoredAssetsHandlingType;
}

interface UseManagedAssetOperationsReturn {
  isAssetWhitelisted: (identifier: string) => boolean;
  useIsAssetWhitelisted: (identifier: string) => ComputedRef<boolean>;
  loadingIgnore: DeepReadonly<Ref<string | undefined>>;
  loadingSpam: DeepReadonly<Ref<string | undefined>>;
  loadingWhitelist: DeepReadonly<Ref<string | undefined>>;
  massIgnore: (ignored: boolean) => Promise<void>;
  massSpam: () => Promise<void>;
  toggleIgnoreAsset: (asset: SupportedAsset) => Promise<void>;
  toggleSpam: (item: SupportedAsset) => Promise<void>;
  toggleWhitelistAsset: (identifier: string) => Promise<void>;
}

export function useManagedAssetOperations(
  onRefresh: () => void,
  ignoredFilter: Ref<IgnoredFilter>,
  selected: Ref<string[]>,
): UseManagedAssetOperationsReturn {
  const { t } = useI18n({ useScope: 'global' });

  const { showErrorMessage } = useNotifications();
  const { ignoreAssetWithConfirmation } = useIgnoredAssetConfirmation();
  const { ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
  const { isAssetIgnored, isAssetWhitelisted, useIsAssetWhitelisted } = useAssetsStore();
  const { unWhitelistAsset, whitelistAsset } = useWhitelistedAssetOperations();
  const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();
  const { refetchAssetInfo } = useAssetInfoRetrieval();

  const isSpamAsset = (asset: SupportedAsset): boolean => asset.protocol === 'spam';

  const loadingIgnore = ref<string | undefined>(undefined);
  const loadingWhitelist = ref<string | undefined>(undefined);
  const loadingSpam = ref<string | undefined>(undefined);

  function refreshAssetsConditionally(): void {
    if (get(ignoredFilter).ignoredAssetsHandling !== 'none')
      onRefresh();
  }

  const toggleIgnoreAsset = async (asset: SupportedAsset): Promise<void> => {
    const { identifier, name, symbol } = asset;
    set(loadingIgnore, identifier);
    try {
      if (isAssetIgnored(identifier)) {
        await unignoreAsset(identifier);
        refreshAssetsConditionally();
      }
      else {
        await ignoreAssetWithConfirmation(identifier, symbol || name, refreshAssetsConditionally);
      }
    }
    finally {
      set(loadingIgnore, undefined);
    }
  };

  const toggleSpam = async (item: SupportedAsset): Promise<void> => {
    const { identifier } = item;
    set(loadingSpam, identifier);
    try {
      if (isSpamAsset(item))
        await removeAssetFromSpamList(identifier);
      else
        await markAssetsAsSpam([identifier]);

      refetchAssetInfo(identifier);
      onRefresh();
    }
    finally {
      set(loadingSpam, undefined);
    }
  };

  const toggleWhitelistAsset = async (identifier: string): Promise<void> => {
    set(loadingWhitelist, identifier);
    try {
      if (isAssetWhitelisted(identifier))
        await unWhitelistAsset(identifier);
      else
        await whitelistAsset(identifier);

      onRefresh();
    }
    finally {
      set(loadingWhitelist, undefined);
    }
  };

  const massIgnore = async (ignored: boolean): Promise<void> => {
    const ids = get(selected)
      .filter((identifier) => {
        const isItemIgnored = isAssetIgnored(identifier);
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
    else
      status = await unignoreAsset(ids);

    if (status.success) {
      set(selected, []);
      refreshAssetsConditionally();
    }
  };

  const massSpam = async (): Promise<void> => {
    const ids = get(selected).filter(uniqueStrings);

    if (ids.length === 0) {
      showErrorMessage(t('ignore.spam.no_items.title'), t('ignore.spam.no_items.description'));
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
    loadingIgnore: readonly(loadingIgnore),
    loadingSpam: readonly(loadingSpam),
    loadingWhitelist: readonly(loadingWhitelist),
    massIgnore,
    massSpam,
    toggleIgnoreAsset,
    toggleSpam,
    toggleWhitelistAsset,
    useIsAssetWhitelisted,
  };
}

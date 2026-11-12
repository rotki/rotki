import type { SupportedAsset } from '@rotki/common';
import type { ComputedRef, DeepReadonly, MaybeRefOrGetter, Ref } from 'vue';
import type { IgnoredAssetsHandlingType } from '@/modules/assets/types';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useSelectedAssetIgnoring, useSelectedAssetSpam } from '@/modules/assets/use-selected-asset-actions';
import { useSpamAsset } from '@/modules/assets/use-spam-asset';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';

interface UseManagedAssetOperationsReturn {
  fetchIgnoredAssets: () => Promise<void>;
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
  ignoredHandling: MaybeRefOrGetter<IgnoredAssetsHandlingType>,
  selected: Ref<string[]>,
): UseManagedAssetOperationsReturn {
  const { fetchIgnoredAssets, ignoreAsset, unignoreAsset } = useIgnoredAssetOperations();
  const { ignoreSelected } = useSelectedAssetIgnoring();
  const { markSelectedAsSpam } = useSelectedAssetSpam();
  const { isAssetIgnored, isAssetWhitelisted, useIsAssetWhitelisted } = useAssetsStore();
  const { unWhitelistAsset, whitelistAsset } = useWhitelistedAssetOperations();
  const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();
  const { refetchAssetInfo } = useAssetInfoRetrieval();

  const isSpamAsset = (asset: SupportedAsset): boolean => asset.protocol === 'spam';

  const loadingIgnore = ref<string | undefined>(undefined);
  const loadingWhitelist = ref<string | undefined>(undefined);
  const loadingSpam = ref<string | undefined>(undefined);

  function refreshAssetsConditionally(): void {
    if (toValue(ignoredHandling) !== 'none')
      onRefresh();
  }

  const toggleIgnoreAsset = async (asset: SupportedAsset): Promise<void> => {
    const { identifier } = asset;
    set(loadingIgnore, identifier);
    try {
      if (isAssetIgnored(identifier)) {
        await unignoreAsset(identifier);
        refreshAssetsConditionally();
      }
      else if ((await ignoreAsset(identifier)).success) {
        refreshAssetsConditionally();
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
    if (await ignoreSelected(get(selected), ignored)) {
      set(selected, []);
      refreshAssetsConditionally();
    }
  };

  const massSpam = async (): Promise<void> => {
    if (await markSelectedAsSpam(get(selected))) {
      set(selected, []);
      refreshAssetsConditionally();
    }
  };

  return {
    fetchIgnoredAssets,
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

import type { ComputedRef, DeepReadonly, Ref } from 'vue';
import { useSpamAsset } from '@/composables/assets/spam';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useIgnoredAssetConfirmation } from '@/modules/assets/use-ignored-asset-confirmation';
import { useIgnoredAssetOperations } from '@/modules/assets/use-ignored-asset-operations';
import { useWhitelistedAssetOperations } from '@/modules/assets/use-whitelisted-asset-operations';

interface AssetWithSpamStatus {
  isSpam?: boolean;
  name?: string | null;
  symbol?: string | null;
  [key: string]: unknown;
}

interface UseAssetPageActionsOptions {
  /** The resolved asset data, including spam status */
  asset: ComputedRef<AssetWithSpamStatus | null>;
  /** The asset identifier */
  identifier: Ref<string>;
  /** Callback to refresh asset info after an action */
  refetchAssetInfo: (id: string) => void;
}

interface UseAssetPageActionsReturn {
  isIgnored: ComputedRef<boolean>;
  isSpam: ComputedRef<boolean>;
  loadingIgnore: DeepReadonly<Ref<boolean>>;
  loadingSpam: DeepReadonly<Ref<boolean>>;
  loadingWhitelist: DeepReadonly<Ref<boolean>>;
  toggleIgnoreAsset: () => Promise<void>;
  toggleSpam: () => Promise<void>;
  toggleWhitelistAsset: () => Promise<void>;
}

export function useAssetPageActions(options: UseAssetPageActionsOptions): UseAssetPageActionsReturn {
  const { asset, identifier, refetchAssetInfo } = options;

  const { ignoreAssetWithConfirmation } = useIgnoredAssetConfirmation();
  const { unignoreAsset } = useIgnoredAssetOperations();
  const { useIsAssetIgnored, useIsAssetWhitelisted } = useAssetsStore();
  const { unWhitelistAsset, whitelistAsset } = useWhitelistedAssetOperations();
  const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();

  const isIgnored = useIsAssetIgnored(identifier);
  const isWhitelisted = useIsAssetWhitelisted(identifier);
  const isSpam = computed<boolean>(() => get(asset)?.isSpam || false);

  const loadingIgnore = shallowRef<boolean>(false);
  const loadingWhitelist = shallowRef<boolean>(false);
  const loadingSpam = shallowRef<boolean>(false);

  async function toggleSpam(): Promise<void> {
    set(loadingSpam, true);
    try {
      const id = get(identifier);
      if (get(isSpam))
        await removeAssetFromSpamList(id);
      else
        await markAssetsAsSpam([id]);

      refetchAssetInfo(id);
    }
    finally {
      set(loadingSpam, false);
    }
  }

  async function toggleIgnoreAsset(): Promise<void> {
    set(loadingIgnore, true);
    try {
      const id = get(identifier);
      if (get(isIgnored)) {
        await unignoreAsset(id);
      }
      else {
        const info = get(asset);
        await ignoreAssetWithConfirmation(id, info?.symbol || info?.name);
      }
    }
    finally {
      set(loadingIgnore, false);
    }
  }

  async function toggleWhitelistAsset(): Promise<void> {
    set(loadingWhitelist, true);
    try {
      const id = get(identifier);
      if (get(isWhitelisted))
        await unWhitelistAsset(id);
      else
        await whitelistAsset(id);

      refetchAssetInfo(id);
    }
    finally {
      set(loadingWhitelist, false);
    }
  }

  return {
    isIgnored,
    isSpam,
    loadingIgnore: readonly(loadingIgnore),
    loadingSpam: readonly(loadingSpam),
    loadingWhitelist: readonly(loadingWhitelist),
    toggleIgnoreAsset,
    toggleSpam,
    toggleWhitelistAsset,
  };
}

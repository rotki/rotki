import type { ComputedRef, Ref } from 'vue';
import { useSpamAsset } from '@/composables/assets/spam';
import { useIgnoredAssetsStore } from '@/store/assets/ignored';
import { useWhitelistedAssetsStore } from '@/store/assets/whitelisted';

interface AssetWithSpamStatus {
  isSpam?: boolean;
  [key: string]: unknown;
}

interface UseAssetPageActionsOptions {
  asset: ComputedRef<AssetWithSpamStatus | null>;
  identifier: Ref<string>;
  name: ComputedRef<string | undefined>;
  refetchAssetInfo: (id: string) => void;
  symbol: ComputedRef<string | undefined>;
}

interface UseAssetPageActionsReturn {
  isIgnored: ComputedRef<boolean>;
  isSpam: ComputedRef<boolean>;
  loadingIgnore: Ref<boolean>;
  loadingSpam: Ref<boolean>;
  loadingWhitelist: Ref<boolean>;
  toggleIgnoreAsset: () => Promise<void>;
  toggleSpam: () => Promise<void>;
  toggleWhitelistAsset: () => Promise<void>;
}

export function useAssetPageActions(options: UseAssetPageActionsOptions): UseAssetPageActionsReturn {
  const { asset, identifier, name, refetchAssetInfo, symbol } = options;

  const { ignoreAssetWithConfirmation, unignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();
  const { useIsAssetWhitelisted, unWhitelistAsset, whitelistAsset } = useWhitelistedAssetsStore();
  const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();

  const isIgnored = useIsAssetIgnored(identifier);
  const isWhitelisted = useIsAssetWhitelisted(identifier);
  const isSpam = computed<boolean>(() => get(asset)?.isSpam || false);

  const loadingIgnore = ref<boolean>(false);
  const loadingWhitelist = ref<boolean>(false);
  const loadingSpam = ref<boolean>(false);

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
        await ignoreAssetWithConfirmation(id, get(symbol) || get(name));
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
    loadingIgnore,
    loadingSpam,
    loadingWhitelist,
    toggleIgnoreAsset,
    toggleSpam,
    toggleWhitelistAsset,
  };
}

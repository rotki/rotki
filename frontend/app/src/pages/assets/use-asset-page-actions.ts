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
  toggleIgnoreAsset: () => Promise<void>;
  toggleSpam: () => Promise<void>;
  toggleWhitelistAsset: () => Promise<void>;
}

export function useAssetPageActions(options: UseAssetPageActionsOptions): UseAssetPageActionsReturn {
  const { asset, identifier, name, refetchAssetInfo, symbol } = options;

  const { ignoreAssetWithConfirmation, unignoreAsset, useIsAssetIgnored } = useIgnoredAssetsStore();
  const { isAssetWhitelisted, unWhitelistAsset, whitelistAsset } = useWhitelistedAssetsStore();
  const { markAssetsAsSpam, removeAssetFromSpamList } = useSpamAsset();

  const isIgnored = useIsAssetIgnored(identifier);
  const isWhitelisted = isAssetWhitelisted(identifier);
  const isSpam = computed<boolean>(() => get(asset)?.isSpam || false);

  async function toggleSpam(): Promise<void> {
    const id = get(identifier);
    if (get(isSpam))
      await removeAssetFromSpamList(id);
    else
      await markAssetsAsSpam([id]);

    refetchAssetInfo(id);
  }

  async function toggleIgnoreAsset(): Promise<void> {
    const id = get(identifier);
    if (get(isIgnored)) {
      await unignoreAsset(id);
    }
    else {
      await ignoreAssetWithConfirmation(id, get(symbol) || get(name));
    }
  }

  async function toggleWhitelistAsset(): Promise<void> {
    const id = get(identifier);
    if (get(isWhitelisted))
      await unWhitelistAsset(id);
    else
      await whitelistAsset(id);

    refetchAssetInfo(id);
  }

  return {
    isIgnored,
    isSpam,
    toggleIgnoreAsset,
    toggleSpam,
    toggleWhitelistAsset,
  };
}

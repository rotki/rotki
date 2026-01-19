import type { ComputedRef, Ref } from 'vue';
import type { Collection } from '@/types/collection';
import { getAddressFromEvmIdentifier, isEvmIdentifier, type SupportedAsset, toSentenceCase } from '@rotki/common';
import { CUSTOM_ASSET } from '@/types/asset';

export interface AssetDisplay {
  customAssetType: string;
  evmChain: string | null | undefined;
  identifier: string;
  isCustomAsset: boolean;
  name: string;
  protocol: string | null | undefined;
  symbol: string;
}

interface UseAssetDisplayHelpersReturn {
  canBeEdited: (asset: SupportedAsset) => boolean;
  canBeIgnored: (asset: SupportedAsset) => boolean;
  disabledRows: ComputedRef<SupportedAsset[]>;
  formatType: (string?: string | null) => string;
  getAsset: (item: SupportedAsset) => AssetDisplay;
}

export function useAssetDisplayHelpers(
  collection: Ref<Collection<SupportedAsset>>,
  useIsAssetWhitelisted: (identifier: string) => ComputedRef<boolean>,
): UseAssetDisplayHelpersReturn {
  const formatType = (string?: string | null): string => toSentenceCase(string ?? 'EVM token');

  const getName = (item: SupportedAsset): string => {
    if (item.name) {
      return item.name;
    }
    else if (item.symbol) {
      return item.symbol;
    }
    else if (isEvmIdentifier(item.identifier)) {
      return getAddressFromEvmIdentifier(item.identifier);
    }
    else {
      return item.identifier;
    }
  };

  const getAsset = (item: SupportedAsset): AssetDisplay => ({
    customAssetType: item.customAssetType ?? '',
    evmChain: item.evmChain,
    identifier: item.identifier,
    isCustomAsset: item.assetType === CUSTOM_ASSET,
    name: getName(item),
    protocol: item.protocol,
    symbol: item.symbol ?? '',
  });

  const isSpamAsset = (asset: SupportedAsset): boolean => asset.protocol === 'spam';
  const isCustomAsset = (asset: SupportedAsset): boolean => asset.assetType === CUSTOM_ASSET;
  const canBeIgnored = (asset: SupportedAsset): boolean => !isCustomAsset(asset);
  const canBeEdited = (asset: SupportedAsset): boolean => !isCustomAsset(asset);

  const disabledRows = computed<SupportedAsset[]>(() => {
    const data = get(collection).data;
    return data.filter(item => get(useIsAssetWhitelisted(item.identifier)) || isSpamAsset(item));
  });

  return {
    canBeEdited,
    canBeIgnored,
    disabledRows,
    formatType,
    getAsset,
  };
}

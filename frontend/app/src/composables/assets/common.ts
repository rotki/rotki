import type { ComputedRef } from 'vue';
import { type AssetInfo, getAddressFromEvmIdentifier, isEvmIdentifier } from '@rotki/common';
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CUSTOM_ASSET } from '@/types/asset';

export function useAssetAssociationMap(): ComputedRef<Record<string, string>> {
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());

  return computed<Record<string, string>>(() => {
    const associationMap: Record<string, string> = {};
    if (get(treatEth2AsEth))
      associationMap.ETH2 = 'ETH';

    return associationMap;
  });
}

export function getAssociatedAssetIdentifier(identifier: string, associationMap: Record<string, string>): string {
  return associationMap[identifier] ?? identifier;
}

export function getAssetNameFallback(id: string): string {
  if (isEvmIdentifier(id)) {
    const address = getAddressFromEvmIdentifier(id);
    return `EVM Token: ${address}`;
  }
  return '';
}

export function processAssetInfo(
  data: AssetInfo | null,
  id: string,
  collectionData: AssetInfo | null,
): AssetInfo | null {
  if (!data) {
    const fallback = getAssetNameFallback(id);
    if (!fallback) {
      return null;
    }

    return {
      name: fallback,
      symbol: fallback,
    };
  }

  const isCustomAsset = data.isCustomAsset || data.assetType === CUSTOM_ASSET;

  if (isCustomAsset) {
    return {
      ...data,
      isCustomAsset,
      symbol: data.name,
    };
  }

  const fallback = getAssetNameFallback(id);
  const name = collectionData?.name || data.name || fallback;
  const symbol = collectionData?.symbol || data.symbol || fallback;

  return {
    ...data,
    isCustomAsset,
    name,
    symbol,
  };
}

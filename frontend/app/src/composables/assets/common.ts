import { type AssetInfo, getAddressFromEvmIdentifier, isEvmIdentifier } from '@rotki/common';
import { CUSTOM_ASSET } from '@/modules/assets/types';
import { useGeneralSettingsStore } from '@/store/settings/general';

export function useResolveAssetIdentifier(): (identifier: string) => string {
  const { treatEth2AsEth } = storeToRefs(useGeneralSettingsStore());

  return (identifier: string): string => {
    if (get(treatEth2AsEth) && identifier === 'ETH2')
      return 'ETH';

    return identifier;
  };
}

function getAssetNameFallback(id: string): string {
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

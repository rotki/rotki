import { type AssetInfo, getAddressFromEvmIdentifier, isEvmIdentifier } from '@rotki/common';
import { CUSTOM_ASSET } from '@/modules/assets/types';
import { useSetting } from '@/modules/settings/use-setting';

export function useResolveAssetIdentifier(): (identifier: string) => string {
  const treatEth2AsEth = useSetting('treatEth2AsEth');

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

/** With nothing resolved, the identifier itself is the only name available. */
function fallbackAssetInfo(id: string): AssetInfo | null {
  const fallback = getAssetNameFallback(id);
  if (!fallback)
    return null;

  return {
    name: fallback,
    symbol: fallback,
  };
}

/** A collection parent names its members, so its name wins over the asset's own. */
function resolveDisplayNames(
  data: AssetInfo,
  id: string,
  collectionData: AssetInfo | null,
): { name?: string; symbol?: string } {
  const fallback = getAssetNameFallback(id);

  return {
    name: (collectionData?.name ?? data.name) ?? fallback,
    symbol: (collectionData?.symbol ?? data.symbol) ?? fallback,
  };
}

export function processAssetInfo(
  data: AssetInfo | null,
  id: string,
  collectionData: AssetInfo | null,
): AssetInfo | null {
  if (!data)
    return fallbackAssetInfo(id);

  const isCustomAsset = data.isCustomAsset ?? data.assetType === CUSTOM_ASSET;

  if (isCustomAsset) {
    return {
      ...data,
      isCustomAsset,
      symbol: data.name,
    };
  }

  return {
    ...data,
    isCustomAsset,
    ...resolveDisplayNames(data, id, collectionData),
  };
}

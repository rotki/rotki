import { type AssetWithResolutionStatus, useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { useAssetsStore } from '@/modules/assets/use-assets-store';

/**
 * Whether resolved asset metadata identifies a curated token (CoinGecko, CryptoCompare, or
 * collection membership).
 *
 * @remarks
 * Colibri runs the provenance-disabled model export, so canonical curated tokens can score above
 * threshold on metadata alone. Data-issue and reconciliation surfaces use this check to skip
 * calling them out as potential spam.
 */
export function isCuratedAssetInfo(info: AssetWithResolutionStatus | null | undefined): boolean {
  return Boolean(info?.resolved && [info.coingecko, info.cryptocompare, info.collectionId].some(Boolean));
}

interface UseSpamTokenTrustReturn {
  isTrustedForSpamDisplay: (identifier?: string | null) => boolean;
}

/**
 * Identifies tokens whose spam-model flags should not be surfaced as potential spam.
 *
 * @remarks
 * Colibri runs the provenance-disabled model export, so canonical curated tokens and
 * user-whitelisted false positives can score above threshold; data-issue and reconciliation
 * surfaces skip calling them out as potential spam.
 */
export function useSpamTokenTrust(): UseSpamTokenTrustReturn {
  const assetsStore = useAssetsStore();
  const { getAssetInfo } = useAssetInfoRetrieval();

  const isTrustedForSpamDisplay = (identifier?: string | null): boolean => {
    if (!identifier)
      return false;

    return assetsStore.isAssetWhitelisted(identifier) || isCuratedAssetInfo(getAssetInfo(identifier));
  };

  return { isTrustedForSpamDisplay };
}

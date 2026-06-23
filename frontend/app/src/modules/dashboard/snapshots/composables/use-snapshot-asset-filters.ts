import { useAssetInfoCache } from '@/modules/assets/use-asset-info-cache';
import { useAssetsStore } from '@/modules/assets/use-assets-store';
import { useResolveAssetIdentifier } from '@/modules/assets/use-resolve-asset-identifier';

interface UseSnapshotAssetFiltersReturn {
  /** Whether the asset is spam (valueless by nature) per already-resolved info. */
  isSpamAsset: (assetIdentifier: string) => boolean;
  /** Whether the asset is on the user's ignored list. */
  isIgnoredAsset: (assetIdentifier: string) => boolean;
}

/**
 * Predicates the snapshot editor uses to hide clutter rows and to keep them out
 * of the zero-value sanity warning — spam and ignored assets. Centralised so the
 * balances table and the summary warning agree on what counts.
 *
 * Crucially these must NOT trigger asset resolution. `getAssetInfo` is a DISPLAY
 * path: it queues a `/assets/mappings` fetch for every unresolved identifier, so
 * checking spam across a whole snapshot would reload hundreds of assets. Instead:
 * - spam is read straight from the asset-info cache RECORD (no queue, no fetch);
 *   assets not yet resolved read as non-spam, and any spam asset is also on the
 *   ignored list anyway (marking spam auto-ignores — see use-spam-asset.ts).
 * - ignored is a plain lookup in the preloaded `ignoredAssets` list.
 *
 * Both reads are reactive (they read the cache ref / ignored list), so a
 * consuming `computed` re-evaluates as assets resolve or the lists change.
 */
export function useSnapshotAssetFilters(): UseSnapshotAssetFiltersReturn {
  const { cache } = useAssetInfoCache();
  const { isAssetIgnored } = useAssetsStore();
  const resolveAssetIdentifier = useResolveAssetIdentifier();

  function isSpamAsset(assetIdentifier: string): boolean {
    const info = get(cache)[resolveAssetIdentifier(assetIdentifier)];
    return info?.isSpam === true || info?.protocol === 'spam';
  }

  return { isIgnoredAsset: isAssetIgnored, isSpamAsset };
}

import { isEvmIdentifier } from '@rotki/common';
import { useManualBalanceData } from '@/modules/balances/manual/use-manual-balance-data';
import { useSnapshotAssetFilters } from '@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters';

/**
 * Whether a snapshot row's asset can be marked as spam while removing the row.
 *
 * - `eligible`: the option is offered.
 * - `manual-balance`: offered disabled, since a manual balance holds the asset.
 * - `unavailable`: not offered at all.
 */
export const SnapshotSpamEligibility = {
  ELIGIBLE: 'eligible',
  MANUAL_BALANCE: 'manual-balance',
  UNAVAILABLE: 'unavailable',
} as const;

export type SnapshotSpamEligibility = typeof SnapshotSpamEligibility[keyof typeof SnapshotSpamEligibility];

interface UseSnapshotSpamEligibilityReturn {
  spamEligibility: (assetIdentifier: string) => SnapshotSpamEligibility;
}

/**
 * Decides which snapshot rows offer "remove and mark as spam".
 *
 * @remarks
 * Only EVM tokens qualify, a narrower set than `isSpammableAssetType`, which also admits Solana
 * tokens. Marking an asset as spam also ignores it, and the EVM token balance query skips ignored
 * tokens, so the token stays out of future snapshots. The Solana token query does not skip them yet,
 * so a Solana token marked here would keep coming back. The check reads the identifier rather than
 * the asset type, so it never triggers asset resolution.
 *
 * An ignored asset has nothing left to mark, and every spam asset is ignored. One held in a manual
 * balance is refused by `useSpamAsset`, so the option is shown disabled rather than failing on save.
 */
export function useSnapshotSpamEligibility(): UseSnapshotSpamEligibilityReturn {
  const { isIgnoredAsset } = useSnapshotAssetFilters();
  const { manualBalancesAssets } = useManualBalanceData();

  function spamEligibility(assetIdentifier: string): SnapshotSpamEligibility {
    if (!isEvmIdentifier(assetIdentifier) || isIgnoredAsset(assetIdentifier))
      return SnapshotSpamEligibility.UNAVAILABLE;
    if (get(manualBalancesAssets).includes(assetIdentifier))
      return SnapshotSpamEligibility.MANUAL_BALANCE;
    return SnapshotSpamEligibility.ELIGIBLE;
  }

  return { spamEligibility };
}

import type { BigNumber } from '@rotki/common';
import type { Snapshot } from '@/modules/dashboard/snapshots';
import { applySetTotal, approxEqualUsd, cloneSnapshot } from '@/modules/dashboard/snapshots/utils/snapshot-math';
import { assetsTotal, getTotalValue, locationsTotal, nftsTotal } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

/**
 * Whether a freshly loaded snapshot's stored total excludes NFT value.
 *
 * @returns true only when the total clearly tracks assets minus NFTs rather than the full assets
 */
export function inferExcludeNfts(snapshot: Snapshot): boolean {
  const assets = assetsTotal(snapshot.balancesSnapshot);
  const stored = getTotalValue(snapshot.locationDataSnapshot);
  const tracksFullAssets = approxEqualUsd(stored, assets);
  const tracksAssetsExNfts = approxEqualUsd(stored, assets.minus(nftsTotal(snapshot.balancesSnapshot)));
  return !tracksFullAssets && tracksAssetsExNfts;
}

/** The total the auto-tracker should hold for the given snapshot. */
export function trackedTotal(snapshot: Snapshot, excludeNfts: boolean): BigNumber {
  const assets = assetsTotal(snapshot.balancesSnapshot);
  return excludeNfts ? assets.minus(nftsTotal(snapshot.balancesSnapshot)) : assets;
}

/**
 * Re-asserts the stored total to the tracked net worth, counteracting the balance rebuild's
 * recompute. The total always tracks the balances, so this runs on load and after every balance
 * mutation or NFT-flag change.
 */
export function retrackTotal(snapshot: Snapshot, excludeNfts: boolean): Snapshot {
  return applySetTotal(snapshot, trackedTotal(snapshot, excludeNfts));
}

/**
 * The draft a loaded snapshot opens as.
 *
 * @remarks
 * Net worth always tracks the balances, so a stale stored total is corrected here and shows as an
 * unsaved change against the untouched original, which is what lets the user save it. Drift
 * within the reconciliation epsilon is kept as stored, so rounding noise never reads as a change.
 *
 * A total is only stale when the locations agree with the balances. When they do not, the total
 * is one side of a mismatch the banner resolves, and correcting it on load would make an
 * untouched snapshot read as edited and let a plain save write the unresolved balances sum.
 */
export function seedDraft(snapshot: Snapshot, excludeNfts: boolean): Snapshot {
  const copy = cloneSnapshot(snapshot);
  const tracked = trackedTotal(copy, excludeNfts);
  if (approxEqualUsd(getTotalValue(copy.locationDataSnapshot), tracked))
    return copy;
  if (!approxEqualUsd(locationsTotal(copy.locationDataSnapshot), tracked))
    return copy;
  return retrackTotal(copy, excludeNfts);
}

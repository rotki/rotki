import type { BigNumber } from '@rotki/common';
import type { BalanceSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import type { LocationBalancePreview } from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { assetsTotal, locationsTotal, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

/**
 * Rebuilds a snapshot after its balance rows change (add / edit / delete).
 *
 * The affected `location` subtotal is updated to `locationBalance.after` (a new
 * location row is appended when it doesn't exist yet), and the synthetic
 * `total` row is recomputed from the net of all balances. All values are USD.
 *
 * @param params.snapshot the current snapshot (read for its location rows)
 * @param params.balancesSnapshot the new balance rows to store
 * @param params.location the location whose subtotal changed ('' to skip)
 * @param params.locationBalance the `{ before, after }` for that location
 * @param params.timestamp the snapshot timestamp (for a newly created row)
 */
export function rebuildSnapshotAfterBalanceChange(params: {
  snapshot: Snapshot;
  balancesSnapshot: BalanceSnapshot[];
  location: string;
  locationBalance: LocationBalancePreview | null;
  timestamp: number;
}): Snapshot {
  const { balancesSnapshot, location, locationBalance, snapshot, timestamp } = params;
  const locationDataSnapshot = [...snapshot.locationDataSnapshot];

  if (location && locationBalance) {
    const locationDataIndex = locationDataSnapshot.findIndex(item => item.location === location);
    if (locationDataIndex > -1)
      locationDataSnapshot[locationDataIndex].usdValue = locationBalance.after;
    else
      locationDataSnapshot.push({ location, timestamp, usdValue: locationBalance.after });
  }

  const totalDataIndex = locationDataSnapshot.findIndex(item => item.location === TOTAL_LOCATION);
  if (totalDataIndex > -1)
    locationDataSnapshot[totalDataIndex].usdValue = assetsTotal(balancesSnapshot);

  return { balancesSnapshot, locationDataSnapshot };
}

/**
 * Removes several balance rows at once without touching any location subtotal.
 *
 * Location subtotals are skipped deliberately: this is the inverse of a delete
 * with no attribution, and the only caller (the bulk cleanup of valueless rows)
 * removes balances whose USD value is zero, so debiting a location would be a
 * no-op anyway. The `total` row is recomputed from the surviving balances. Doing
 * it in one rebuild keeps the whole sweep as a single undo entry.
 */
export function applyBalanceBulkDelete(snapshot: Snapshot, indices: number[]): Snapshot {
  const remove = new Set(indices);
  if (remove.size === 0)
    return snapshot;
  const balancesSnapshot = snapshot.balancesSnapshot.filter((_, i) => !remove.has(i));
  const timestamp = snapshot.balancesSnapshot[0]?.timestamp ?? 0;
  return rebuildSnapshotAfterBalanceChange({ balancesSnapshot, location: '', locationBalance: null, snapshot, timestamp });
}

/**
 * Reconciles a snapshot whose location subtotals don't add up to its net worth:
 * absorbs the whole difference (`targetTotal − locationsSum`) into a single
 * location — created if missing — and snaps the stored total to `targetTotal`.
 * `targetTotal` is the tracked net worth (the balances sum, minus NFTs when they
 * are excluded), so both locations and total land on it. With locations already
 * summing to it the difference is zero, so this just fixes the total. The caller
 * picks the location; the editor pre-selects the largest.
 */
export function applyReconcileLocations(snapshot: Snapshot, location: string, targetTotal: BigNumber): Snapshot {
  const diff = targetTotal.minus(locationsTotal(snapshot.locationDataSnapshot));
  const timestamp = snapshot.locationDataSnapshot[0]?.timestamp ?? snapshot.balancesSnapshot[0]?.timestamp ?? 0;
  const locationDataSnapshot = [...snapshot.locationDataSnapshot];

  const index = locationDataSnapshot.findIndex(item => item.location === location);
  if (index > -1)
    locationDataSnapshot[index] = { ...locationDataSnapshot[index], usdValue: locationDataSnapshot[index].usdValue.plus(diff) };
  else
    locationDataSnapshot.push({ location, timestamp, usdValue: diff });

  const totalIndex = locationDataSnapshot.findIndex(item => item.location === TOTAL_LOCATION);
  if (totalIndex > -1)
    locationDataSnapshot[totalIndex] = { ...locationDataSnapshot[totalIndex], usdValue: targetTotal };
  else
    locationDataSnapshot.push({ location: TOTAL_LOCATION, timestamp, usdValue: targetTotal });

  return { ...snapshot, locationDataSnapshot };
}

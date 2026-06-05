import type { LocationBalancePreview } from '@/modules/dashboard/snapshots/lib/snapshot-location-balance';
import type { BalanceSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { assetsTotal, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/lib/snapshot-totals';

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

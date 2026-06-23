import type { BalanceSnapshot, LocationDataSnapshot, Snapshot, SnapshotPayload } from '@/modules/dashboard/snapshots';
import { BigNumber, bigNumberify } from '@rotki/common';
import {
  locationBalanceAfterDelete,
  locationBalanceAfterEdit,
} from '@/modules/dashboard/snapshots/utils/snapshot-location-balance';
import { rebuildSnapshotAfterBalanceChange } from '@/modules/dashboard/snapshots/utils/snapshot-mutations';
import {
  assetsTotal,
  getTotalEntry,
  getTotalValue,
  locationsTotal,
  TOTAL_LOCATION,
} from '@/modules/dashboard/snapshots/utils/snapshot-totals';

/**
 * Pure draft transforms for the snapshot editor.
 *
 * Every function takes a `Snapshot` and returns a NEW `Snapshot` (no mutation),
 * so the draft model can keep an immutable history for undo. Balance edits
 * reuse the existing location-delta and total-rebuild helpers; location edits
 * touch only the affected location row (the stored `total` row is independent —
 * see `findSumMismatch`). All values are USD.
 */

/** A positive add/delete portion, or an edit's signed per-location USD delta. */
export interface LocationSplit {
  location: string;
  usdValue: BigNumber;
}

/**
 * Where a balance's value is attributed:
 * - `''` — skip location bookkeeping entirely;
 * - a location name — the whole value goes there (the simple, default path);
 * - a split — the value is distributed across locations (caller guarantees the
 *   portions sum to the balance's `usdValue`).
 */
export type LocationAttribution = string | LocationSplit[];

/** A balance edit/add carries the location(s) it should be attributed to. */
export interface BalanceMutation {
  balance: BalanceSnapshot;
  location: LocationAttribution;
}

/** The whole balance attributed to one location ('' skips location bookkeeping). */
function singleEntry(location: string, balance: BalanceSnapshot): LocationSplit[] {
  return location ? [{ location, usdValue: balance.usdValue }] : [];
}

/**
 * Folds the new balance rows + an attribution into a snapshot, updating each
 * touched location subtotal and the stored total.
 *
 * A **string** attributes the whole balance to one location, removing the prior
 * contribution at `editIndex` (single-location add/edit). A **split** is a list
 * of signed per-location USD *deltas* the caller already netted against the old
 * value (an edit distributes `new − old`, an add the full new value), so each
 * location moves by exactly its own share and nothing is removed here — this is
 * what stops a multi-location edit dumping the whole old value on the first row.
 */
function applyBalanceAttribution(params: {
  snapshot: Snapshot;
  balancesSnapshot: BalanceSnapshot[];
  balance: BalanceSnapshot;
  attribution: LocationAttribution;
  editIndex: number | null;
}): Snapshot {
  const { attribution, balance, balancesSnapshot, editIndex, snapshot } = params;
  const isSplit = typeof attribution !== 'string';
  const entries: LocationSplit[] = isSplit ? attribution : singleEntry(attribution, balance);

  if (entries.length === 0) {
    return rebuildSnapshotAfterBalanceChange({
      balancesSnapshot,
      location: '',
      locationBalance: null,
      snapshot,
      timestamp: balance.timestamp,
    });
  }

  return entries.reduce<Snapshot>((acc, entry, i) => {
    const locationBalance = locationBalanceAfterEdit({
      category: balance.category,
      // Only the single-location path removes the old value; split deltas already account for it.
      editIndex: !isSplit && i === 0 ? editIndex : null,
      location: entry.location,
      snapshot: acc,
      usdValue: entry.usdValue,
    });
    return rebuildSnapshotAfterBalanceChange({
      balancesSnapshot,
      location: entry.location,
      locationBalance,
      snapshot: acc,
      timestamp: balance.timestamp,
    });
  }, snapshot);
}

/** Adds a balance row (appended, so existing indices stay stable). */
export function applyBalanceAdd(snapshot: Snapshot, mutation: BalanceMutation): Snapshot {
  const { balance, location } = mutation;
  return applyBalanceAttribution({
    attribution: location,
    balance,
    balancesSnapshot: [...snapshot.balancesSnapshot, balance],
    editIndex: null,
    snapshot,
  });
}

/** Replaces the balance at `index` with `balance`, re-attributed to `location`. */
export function applyBalanceEdit(snapshot: Snapshot, index: number, mutation: BalanceMutation): Snapshot {
  const { balance, location } = mutation;
  const balancesSnapshot = [...snapshot.balancesSnapshot];
  balancesSnapshot[index] = balance;
  return applyBalanceAttribution({
    attribution: location,
    balance,
    balancesSnapshot,
    editIndex: index,
    snapshot,
  });
}

/**
 * Removes the balance at `index`, debiting the location(s) it was attributed to.
 * A single location name (or `''` to skip) takes the original tested path; a
 * split debits each location by its own portion — the inverse of a split add.
 */
export function applyBalanceDelete(snapshot: Snapshot, index: number, location: LocationAttribution): Snapshot {
  const balancesSnapshot = snapshot.balancesSnapshot.filter((_, i) => i !== index);
  const removed = snapshot.balancesSnapshot[index];
  const timestamp = removed?.timestamp ?? 0;

  if (typeof location === 'string') {
    const locationBalance = location ? locationBalanceAfterDelete({ index, location, snapshot }) : null;
    return rebuildSnapshotAfterBalanceChange({ balancesSnapshot, location, locationBalance, snapshot, timestamp });
  }

  if (!removed)
    return rebuildSnapshotAfterBalanceChange({ balancesSnapshot, location: '', locationBalance: null, snapshot, timestamp });

  // Removing a portion is the inverse of adding it: debit each location by its share.
  return location.reduce<Snapshot>((acc, entry) => {
    const locationBalance = locationBalanceAfterEdit({
      category: removed.category,
      editIndex: null,
      location: entry.location,
      snapshot: acc,
      usdValue: entry.usdValue.negated(),
    });
    return rebuildSnapshotAfterBalanceChange({
      balancesSnapshot,
      location: entry.location,
      locationBalance,
      snapshot: acc,
      timestamp,
    });
  }, snapshot);
}

/** Appends a location row (caller guarantees the location is not duplicated). */
export function applyLocationAdd(snapshot: Snapshot, location: LocationDataSnapshot): Snapshot {
  return {
    ...snapshot,
    locationDataSnapshot: [...snapshot.locationDataSnapshot, location],
  };
}

/** Sets the USD value of the location row at `index`. */
export function applyLocationEdit(snapshot: Snapshot, index: number, location: LocationDataSnapshot): Snapshot {
  const locationDataSnapshot = [...snapshot.locationDataSnapshot];
  locationDataSnapshot[index] = location;
  return { ...snapshot, locationDataSnapshot };
}

/** Removes the location row at `index`. */
export function applyLocationDelete(snapshot: Snapshot, index: number): Snapshot {
  return {
    ...snapshot,
    locationDataSnapshot: snapshot.locationDataSnapshot.filter((_, i) => i !== index),
  };
}

/**
 * Sets several location subtotals to absolute USD values in one step, creating
 * rows that don't exist yet. Used to *distribute* a reconciliation across
 * multiple locations (caller decides the per-location values). Leaves the stored
 * `total` row untouched — consistent with `applyLocationEdit`; reconciling the
 * total is a separate, explicit step.
 */
export function distributeToLocations(snapshot: Snapshot, splits: LocationSplit[]): Snapshot {
  const locationDataSnapshot = [...snapshot.locationDataSnapshot];
  const timestamp = locationDataSnapshot[0]?.timestamp ?? snapshot.balancesSnapshot[0]?.timestamp ?? 0;

  for (const { location, usdValue } of splits) {
    const index = locationDataSnapshot.findIndex(item => item.location === location);
    if (index > -1)
      locationDataSnapshot[index] = { ...locationDataSnapshot[index], usdValue };
    else
      locationDataSnapshot.push({ location, timestamp, usdValue });
  }

  return { ...snapshot, locationDataSnapshot };
}

/**
 * Sets the stored `total` row to `usdValue` (the value the net-worth chart
 * plots). Creates the row when absent. This is deliberately independent of the
 * two panel sums — the user is the source of truth for the canonical net worth.
 */
export function applySetTotal(snapshot: Snapshot, usdValue: BigNumber): Snapshot {
  const locationDataSnapshot = [...snapshot.locationDataSnapshot];
  const totalEntry = getTotalEntry(locationDataSnapshot);
  const timestamp = totalEntry?.timestamp ?? snapshot.balancesSnapshot[0]?.timestamp ?? 0;
  const index = locationDataSnapshot.findIndex(item => item.location === TOTAL_LOCATION);

  if (index > -1)
    locationDataSnapshot[index] = { ...locationDataSnapshot[index], usdValue };
  else
    locationDataSnapshot.push({ location: TOTAL_LOCATION, timestamp, usdValue });

  return { ...snapshot, locationDataSnapshot };
}

export interface SnapshotSumMismatch {
  /** Net of all balance rows (assets minus liabilities), USD. */
  balancesSum: BigNumber;
  /** Sum of the real (non-`total`) location rows, USD. */
  locationsSum: BigNumber;
  /** Value of the stored `total` row — what the chart plots, USD. */
  storedTotal: BigNumber;
}

/**
 * Absorbs floating-point / CSV-import noise: the larger of one cent and a tiny
 * fraction of the total. Keeps a few wei of drift from raising the banner while
 * still surfacing a real discrepancy.
 */
function defaultEpsilon(storedTotal: BigNumber): BigNumber {
  return BigNumber.max(storedTotal.abs().multipliedBy(1e-8), bigNumberify(0.01));
}

/**
 * Reconciles the three scalar totals of a snapshot. Returns `null` when all
 * three agree within `epsilon`, otherwise the three values so the banner can
 * show the breakdown. Per-location reconciliation is impossible (no join key
 * between balances and locations), so this compares the scalars only.
 */
export function findSumMismatch(snapshot: Snapshot, epsilon?: BigNumber, balancesSumOverride?: BigNumber): SnapshotSumMismatch | null {
  const balancesSum = balancesSumOverride ?? assetsTotal(snapshot.balancesSnapshot);
  const locationsSum = locationsTotal(snapshot.locationDataSnapshot);
  const storedTotal = getTotalValue(snapshot.locationDataSnapshot);

  const eps = epsilon ?? defaultEpsilon(storedTotal);
  const within = (a: BigNumber, b: BigNumber): boolean => a.minus(b).abs().lte(eps);

  if (within(balancesSum, locationsSum) && within(balancesSum, storedTotal) && within(locationsSum, storedTotal))
    return null;

  return { balancesSum, locationsSum, storedTotal };
}

/**
 * Whether two USD scalars agree within the default reconciliation epsilon (a
 * cent, or a tiny fraction of the larger magnitude). Used to infer whether a
 * loaded snapshot's stored total already tracks the balances.
 */
export function approxEqualUsd(a: BigNumber, b: BigNumber, epsilon?: BigNumber): boolean {
  const eps = epsilon ?? defaultEpsilon(BigNumber.max(a.abs(), b.abs()));
  return a.minus(b).abs().lte(eps);
}

export type { SnapshotChange } from '@/modules/dashboard/snapshots/utils/snapshot-changes';

export {
  buildSnapshotChanges,
  countSnapshotChanges,
  snapshotsEqual,
} from '@/modules/dashboard/snapshots/utils/snapshot-changes';

/**
 * A structural copy of a snapshot. Rows are shallow-copied; the `BigNumber`
 * values are immutable so sharing their references is safe. Used to keep the
 * draft's `original` baseline insulated from in-place reassignment.
 */
export function cloneSnapshot(snapshot: Snapshot): Snapshot {
  return {
    balancesSnapshot: snapshot.balancesSnapshot.map(item => ({ ...item })),
    locationDataSnapshot: snapshot.locationDataSnapshot.map(item => ({ ...item })),
  };
}

/** Serialises a snapshot into the API payload (BigNumber -> fixed string). */
export function toSnapshotPayload(snapshot: Snapshot): SnapshotPayload {
  return {
    balancesSnapshot: snapshot.balancesSnapshot.map(item => ({
      ...item,
      amount: item.amount.toFixed(),
      usdValue: item.usdValue.toFixed(),
    })),
    locationDataSnapshot: snapshot.locationDataSnapshot.map(item => ({
      ...item,
      usdValue: item.usdValue.toFixed(),
    })),
  };
}

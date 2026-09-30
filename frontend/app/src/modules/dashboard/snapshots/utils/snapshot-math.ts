import type { BalanceSnapshot, LocationDataSnapshot, Snapshot, SnapshotPayload } from '@/modules/dashboard/snapshots';
import { BigNumber, bigNumberify, Zero } from '@rotki/common';
import { bigNumberSum } from '@/modules/core/common/data/calculation';
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
  signedUsdValue,
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

/** Balance rows whose combined value accounts for a sum mismatch. */
export interface MismatchRows {
  indices: number[];
  /** Net USD of those rows. */
  value: BigNumber;
  /** Whether they are the spam and ignored rows, rather than one row that happens to match. */
  excluded: boolean;
  /** What is left of the gap once the rows are gone: zero for an exact match, the typing error otherwise. */
  rest: BigNumber;
}

/** How far spam and ignored rows may sit from the gap and still be offered, as a share of the gap. */
const EXCLUDED_GAP_TOLERANCE = 0.1;

/**
 * The rows a mismatch comes down to, when their value is the amount the balances exceed the
 * locations by. That is what a user leaves behind by lowering the locations and the total to the
 * real holdings while keeping a mispriced row: removing the rows, with no location touched, makes
 * the totals agree again, up to whatever the user got wrong typing the lowered totals, which is
 * left for a reconcile. `null` when nothing accounts for the gap.
 *
 * Any row matches when its value is the gap within the reconciliation epsilon, and only when no
 * other row has the same value, since the offer names one asset. Spam and ignored rows also match
 * within 10% of the gap, since they are what users lower the totals around and those totals are
 * typed by hand; a real asset near a typo gap is too likely to be a coincidence for that.
 *
 * A single spam or ignored row is tried before the whole set, for several spam tokens left out at
 * once. Trying the set first would sweep in a small ignored row the locations do hold.
 */
export function rowsBehindMismatch(
  snapshot: Snapshot,
  mismatch: SnapshotSumMismatch,
  isExcluded: (assetIdentifier: string) => boolean,
): MismatchRows | null {
  const balances = snapshot.balancesSnapshot;
  const gap = mismatch.balancesSum.minus(mismatch.locationsSum);
  const matchesGap = (value: BigNumber): boolean => !value.isZero() && approxEqualUsd(gap, value);
  const nearGap = (value: BigNumber): boolean =>
    !value.isZero() && value.isNegative() === gap.isNegative()
    && gap.minus(value).abs().isLessThanOrEqualTo(gap.abs().multipliedBy(EXCLUDED_GAP_TOLERANCE));

  // Whether removal settles the totals is judged on the sums left afterwards, at their own scale:
  // next to an absurd value the gap's tolerance would swallow a real remainder.
  const found = (indices: number[], value: BigNumber, excluded: boolean): MismatchRows => ({
    excluded,
    indices,
    rest: approxEqualUsd(mismatch.balancesSum.minus(value), mismatch.locationsSum) ? Zero : gap.minus(value),
    value,
  });

  const single = balances.flatMap((item, index) => matchesGap(signedUsdValue(item)) ? [index] : []);
  if (single.length === 1) {
    const row = balances[single[0]];
    return found(single, signedUsdValue(row), isExcluded(row.assetIdentifier));
  }
  if (single.length > 1)
    return null;

  const excluded = balances.flatMap((item, index) => isExcluded(item.assetIdentifier) ? [index] : []);
  const nearSingle = excluded.filter(index => nearGap(signedUsdValue(balances[index])));
  if (nearSingle.length === 1)
    return found(nearSingle, signedUsdValue(balances[nearSingle[0]]), true);

  const excludedValue = bigNumberSum(excluded.map(index => signedUsdValue(balances[index])));
  if (nearSingle.length === 0 && excluded.length > 0 && nearGap(excludedValue))
    return found(excluded, excludedValue, true);
  return null;
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

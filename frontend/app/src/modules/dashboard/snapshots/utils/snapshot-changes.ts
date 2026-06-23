import type { BalanceSnapshot, LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, Zero } from '@rotki/common';
import { TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

function balanceEquals(a: BalanceSnapshot | undefined, b: BalanceSnapshot | undefined): boolean {
  if (a === undefined || b === undefined)
    return a === b;
  return a.category === b.category
    && a.assetIdentifier === b.assetIdentifier
    && a.amount.eq(b.amount)
    && a.usdValue.eq(b.usdValue);
}

function locationEquals(a: LocationDataSnapshot | undefined, b: LocationDataSnapshot | undefined): boolean {
  if (a === undefined || b === undefined)
    return a === b;
  return a.location === b.location && a.usdValue.eq(b.usdValue);
}

/**
 * A single structural difference between two snapshots. The synthetic `total`
 * row is surfaced as its own `total-changed` kind (not a `location-changed`) so
 * the review panel can render the auto-derived net-worth update distinctly.
 */
export type SnapshotChange =
  | { kind: 'balance-added'; index: number; after: BalanceSnapshot }
  | { kind: 'balance-removed'; index: number; before: BalanceSnapshot }
  | { kind: 'balance-changed'; index: number; before: BalanceSnapshot; after: BalanceSnapshot }
  | { kind: 'location-added'; location: string; after: BigNumber }
  | { kind: 'location-removed'; location: string; before: BigNumber }
  | { kind: 'location-changed'; location: string; before: BigNumber; after: BigNumber }
  | { kind: 'total-changed'; before: BigNumber; after: BigNumber };

/** Identity of a balance row: a snapshot holds one row per asset+category. */
function balanceKey(balance: BalanceSnapshot): string {
  return `${balance.category} ${balance.assetIdentifier}`;
}

/**
 * Diffs balance rows by their asset+category identity, NOT by array position:
 * deleting or inserting a row shifts every later index, so a positional compare
 * reports the whole tail as "changed" (one delete in a 600-row snapshot looked
 * like 600 edits). Matching by identity yields only the rows the user touched.
 */
function diffBalanceRows(original: Snapshot, draft: Snapshot): SnapshotChange[] {
  const changes: SnapshotChange[] = [];
  const draftByKey = new Map<string, { balance: BalanceSnapshot; index: number }>();
  draft.balancesSnapshot.forEach((balance, index) => {
    draftByKey.set(balanceKey(balance), { balance, index });
  });

  const seen = new Set<string>();
  // Removed and changed rows, in the original's order.
  original.balancesSnapshot.forEach((before, index) => {
    const key = balanceKey(before);
    seen.add(key);
    const match = draftByKey.get(key);
    if (match === undefined)
      changes.push({ before, index, kind: 'balance-removed' });
    else if (!balanceEquals(before, match.balance))
      changes.push({ after: match.balance, before, index: match.index, kind: 'balance-changed' });
  });

  // Added rows (present in the draft but not the original), in the draft's order.
  draft.balancesSnapshot.forEach((after, index) => {
    if (!seen.has(balanceKey(after)))
      changes.push({ after, index, kind: 'balance-added' });
  });

  return changes;
}

/** The stored `total` pseudo-row, surfaced as its own kind (it's always present). */
function diffTotalRow(before?: LocationDataSnapshot, after?: LocationDataSnapshot): SnapshotChange | undefined {
  if (locationEquals(before, after))
    return undefined;
  return { after: after?.usdValue ?? Zero, before: before?.usdValue ?? Zero, kind: 'total-changed' };
}

function diffLocationRow(name: string, before?: LocationDataSnapshot, after?: LocationDataSnapshot): SnapshotChange | undefined {
  if (locationEquals(before, after))
    return undefined;
  if (before === undefined)
    return after ? { after: after.usdValue, kind: 'location-added', location: name } : undefined;
  if (after === undefined)
    return { before: before.usdValue, kind: 'location-removed', location: name };
  return { after: after.usdValue, before: before.usdValue, kind: 'location-changed', location: name };
}

/**
 * The ordered list of structural differences between two snapshots: changed/
 * added/removed balance rows then added/removed/changed location rows (by name),
 * with the stored `total` row collapsed into a single `total-changed`. Powers the
 * "review changes before save" panel; `countSnapshotChanges` is just its length.
 */
export function buildSnapshotChanges(original: Snapshot, draft: Snapshot): SnapshotChange[] {
  const names = new Set<string>([
    ...original.locationDataSnapshot.map(item => item.location),
    ...draft.locationDataSnapshot.map(item => item.location),
  ]);

  const locationChanges = [...names].flatMap((name) => {
    const before = original.locationDataSnapshot.find(item => item.location === name);
    const after = draft.locationDataSnapshot.find(item => item.location === name);
    const change = name === TOTAL_LOCATION ? diffTotalRow(before, after) : diffLocationRow(name, before, after);
    return change ? [change] : [];
  });

  return [...diffBalanceRows(original, draft), ...locationChanges];
}

/**
 * Counts the structural differences between two snapshots. Drives `isDirty`
 * (count > 0) and the "N unsaved changes" badge.
 */
export function countSnapshotChanges(original: Snapshot, draft: Snapshot): number {
  return buildSnapshotChanges(original, draft).length;
}

/** Whether two snapshots are structurally identical. */
export function snapshotsEqual(a: Snapshot, b: Snapshot): boolean {
  return countSnapshotChanges(a, b) === 0;
}

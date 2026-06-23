import type { BalanceType } from '@/modules/balances/types/balances';
import type { Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { isLiability, TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';

/**
 * Snapshot location-balance preview helpers.
 *
 * Adding, editing or deleting a balance shifts the subtotal of the location it
 * belongs to. These pure helpers compute the resulting `{ before, after }`
 * subtotal so the edit dialog can preview it. The liability sign is the easy
 * thing to get wrong (an edit subtracts the old contribution then adds the new;
 * a delete is the inverse of an add), so it lives here under test. All USD.
 */

export interface LocationBalancePreview {
  before: BigNumber;
  after: BigNumber;
}

/** Sign a balance contributes to a subtotal: +1 for assets, -1 for liabilities. */
function contributionFactor(category: BalanceType): BigNumber {
  return bigNumberify(isLiability(category) ? -1 : 1);
}

/**
 * The subtotal of `location` after adding or editing a balance there.
 *
 * `usdValue`/`category` describe the new balance (USD). When `editIndex` is a
 * number, the previous balance at that index is removed from the subtotal first
 * (an edit = remove old + add new). When the location has no row yet, the
 * preview starts from zero.
 */
export function locationBalanceAfterEdit(params: {
  snapshot: Snapshot;
  location: string;
  usdValue: BigNumber;
  category: BalanceType;
  editIndex: number | null;
}): LocationBalancePreview {
  const { category, editIndex, location, snapshot, usdValue } = params;
  const locationData = snapshot.locationDataSnapshot.find(item => item.location === location);

  if (!locationData)
    return { after: usdValue, before: Zero };

  let usdValueDiff = usdValue.multipliedBy(contributionFactor(category));

  const previous = editIndex === null ? undefined : snapshot.balancesSnapshot[editIndex];
  if (previous)
    usdValueDiff = usdValueDiff.minus(previous.usdValue.multipliedBy(contributionFactor(previous.category)));

  return {
    after: locationData.usdValue.plus(usdValueDiff),
    before: locationData.usdValue,
  };
}

/**
 * The subtotal of `location` after deleting the balance at `index`. Removal is
 * the inverse of an add, so the contribution sign is negated. Returns `null`
 * when the location row or the balance is missing.
 */
export function locationBalanceAfterDelete(params: {
  snapshot: Snapshot;
  location: string;
  index: number;
}): LocationBalancePreview | null {
  const { index, location, snapshot } = params;
  const locationData = snapshot.locationDataSnapshot.find(item => item.location === location);
  const balanceData = snapshot.balancesSnapshot[index];

  if (!locationData || !balanceData)
    return null;

  const usdValueDiff = balanceData.usdValue.multipliedBy(contributionFactor(balanceData.category).negated());

  return {
    after: locationData.usdValue.plus(usdValueDiff),
    before: locationData.usdValue,
  };
}

/**
 * Location names that can't absorb an asset operation without their subtotal
 * going negative — i.e. you'd remove more value than the location holds.
 *
 * Only assets are capped: removing or shrinking a **liability** adds value back
 * to a location (the inverse), and a location may legitimately be net-negative
 * when it carries liabilities, so liability operations are never restricted.
 *
 * `after(location)` returns the previewed subtotal for that location (or `null`
 * when it can't be computed); a location is overdrawn when that result is
 * negative. Used to disable invalid single-location choices in the edit/delete
 * dialogs and to cap each split portion.
 */
export function overdrawnLocationIds(
  snapshot: Snapshot,
  category: BalanceType,
  after: (location: string) => BigNumber | null,
): string[] {
  if (isLiability(category))
    return [];
  return snapshot.locationDataSnapshot
    .filter(item => item.location !== TOTAL_LOCATION)
    .filter((item) => {
      const result = after(item.location);
      return result !== null && result.isNegative();
    })
    .map(item => item.location);
}

/**
 * The location to preselect for an operation: the sole eligible venue, i.e. the
 * only one not in `ineligible` (typically the overdrawn set). Returns `undefined`
 * when several qualify (the user must choose) or none can. Covers both the
 * lone-location case and "only one of several holds enough value".
 */
export function soleEligibleLocation(candidates: string[], ineligible: string[]): string | undefined {
  const eligible = candidates.filter(location => !ineligible.includes(location));
  return eligible.length === 1 ? eligible[0] : undefined;
}

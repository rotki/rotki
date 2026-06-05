import type { Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, bigNumberify, Zero } from '@rotki/common';
import { BalanceType } from '@/modules/balances/types/balances';
import { isLiability } from '@/modules/dashboard/snapshots/lib/snapshot-totals';

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

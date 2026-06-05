import type { BalanceSnapshot, LocationDataSnapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, Zero } from '@rotki/common';
import { isNft } from '@/modules/assets/nft-utils';
import { BalanceType } from '@/modules/balances/types/balances';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

/**
 * Snapshot total helpers.
 *
 * Snapshots are USD-denominated. A snapshot's location rows include a synthetic
 * `total` row that must equal the sum of the real location rows (and of the
 * net balances). These helpers centralise that aggregation — previously
 * re-implemented inline in the balances table, the location table and the
 * total step — so the "subtotals sum to the total" invariant lives in one
 * tested place. All returned values are USD.
 */

/**
 * The synthetic location row holding the snapshot's grand total. It is excluded
 * from location aggregations and is what real location rows must sum to.
 */
export const TOTAL_LOCATION = 'total';

/** Whether a balance subtracts from (rather than adds to) a net total. */
export function isLiability(category: BalanceType): boolean {
  return category === BalanceType.LIABILITY;
}

/**
 * Signed USD contribution of a balance to a net total: assets add, liabilities
 * subtract.
 */
export function signedUsdValue(item: Pick<BalanceSnapshot, 'category' | 'usdValue'>): BigNumber {
  return isLiability(item.category) ? item.usdValue.negated() : item.usdValue;
}

/** Net USD total of all balances (assets minus liabilities). */
export function assetsTotal(balancesSnapshot: BalanceSnapshot[]): BigNumber {
  return bigNumberSum(balancesSnapshot.map(signedUsdValue));
}

/** Net USD total of the NFT balances only (assets minus liabilities). */
export function nftsTotal(balancesSnapshot: BalanceSnapshot[]): BigNumber {
  return bigNumberSum(
    balancesSnapshot.map(item => (isNft(item.assetIdentifier) ? signedUsdValue(item) : Zero)),
  );
}

/** Sum of the real (non-`total`) location rows, in USD. */
export function locationsTotal(locationDataSnapshot: LocationDataSnapshot[]): BigNumber {
  return bigNumberSum(
    locationDataSnapshot
      .filter(item => item.location !== TOTAL_LOCATION)
      .map(item => item.usdValue),
  );
}

/** The synthetic `total` location row, if present. */
export function getTotalEntry(
  locationDataSnapshot: LocationDataSnapshot[],
): LocationDataSnapshot | undefined {
  return locationDataSnapshot.find(item => item.location === TOTAL_LOCATION);
}

/** USD value of the `total` location row, or `Zero` when it is absent. */
export function getTotalValue(locationDataSnapshot: LocationDataSnapshot[]): BigNumber {
  return getTotalEntry(locationDataSnapshot)?.usdValue ?? Zero;
}

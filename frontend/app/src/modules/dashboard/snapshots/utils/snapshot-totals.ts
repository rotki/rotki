import type { BalanceSnapshot, LocationDataSnapshot, Snapshot } from '@/modules/dashboard/snapshots';
import { type BigNumber, Zero } from '@rotki/common';
import { isNft } from '@/modules/assets/nft-utils';
import { BalanceType } from '@/modules/balances/types/balances';
import { bigNumberSum } from '@/modules/core/common/data/calculation';

/**
 * Snapshot total helpers. Every value here is USD, snapshots being USD-denominated.
 *
 * @remarks
 * Aggregate through these rather than summing inline, so the "subtotals sum to the total"
 * invariant holds in one tested place across the balances table, the location table and the total
 * step.
 *
 * @packageDocumentation
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

/** A snapshot's net worth as the snapshot list and the dashboard graph show it. */
export interface ListedNetWorth {
  /** The stored total minus `ignored` and `nfts`. */
  readonly value: BigNumber;
  /** Net USD of the ignored balances. */
  readonly ignored: BigNumber;
  /** Net USD of the NFT balances left out of net value, ignored ones excluded (they are in `ignored`). */
  readonly nfts: BigNumber;
}

/**
 * Mirrors the backend's `get_netvalue_data`, which subtracts ignored assets (and NFTs, when net
 * value leaves them out) from the stored total at query time. The stored total keeps them, so
 * unignoring an asset brings its value back.
 */
export function listedNetWorth(
  snapshot: Snapshot,
  { includeNfts, isIgnored }: { includeNfts: boolean; isIgnored: (identifier: string) => boolean },
): ListedNetWorth {
  const ignored = bigNumberSum(snapshot.balancesSnapshot.map(item =>
    isIgnored(item.assetIdentifier) ? signedUsdValue(item) : Zero,
  ));
  const nfts = includeNfts
    ? Zero
    : bigNumberSum(snapshot.balancesSnapshot.map(item =>
        isNft(item.assetIdentifier) && !isIgnored(item.assetIdentifier) ? signedUsdValue(item) : Zero,
      ));
  const value = getTotalValue(snapshot.locationDataSnapshot).minus(ignored).minus(nfts);
  return { ignored, nfts, value };
}

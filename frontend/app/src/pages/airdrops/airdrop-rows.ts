import type { Airdrop, Airdrops, PoapDeliveryDetails } from '@/modules/airdrops/airdrops';
import { type BigNumber, Zero } from '@rotki/common';

/**
 * A row as the table sees it: `index` is the table's `row-attr`, and `amount` is filled in so the
 * cell never has to deal with an absent one.
 */
export type AirdropWithIndex = Omit<Airdrop, 'amount'> & { index: number; amount: BigNumber };

/** POAP deliveries are the only airdrops stored as a list, so a list is what identifies them. */
export function hasDetails(details?: PoapDeliveryDetails[]): details is PoapDeliveryDetails[] {
  return !!details && details.length > 0;
}

/**
 * Flattens the address-keyed, then source-keyed, response into one row per airdrop, keeping only
 * the given addresses. An empty address list means every address, which is what the pill bar's
 * absent account pill means.
 */
export function flattenAirdrops(data: Airdrops, addresses: string[]): Airdrop[] {
  const result: Airdrop[] = [];
  for (const address in data) {
    if (addresses.length > 0 && !addresses.includes(address))
      continue;

    const airdrop = data[address];
    for (const source in airdrop) {
      const element = airdrop[source];
      if (Array.isArray(element)) {
        result.push({
          address,
          details: element.map(detail => ({ ...detail })),
          source,
        });
      }
      else {
        result.push({
          address,
          source,
          ...element,
        });
      }
    }
  }
  return result;
}

/**
 * Whether a row reads as the given status. An unrecognised status - including the empty one the
 * page starts on - matches everything, so an absent pill is "all".
 *
 * `currentTimeSeconds` is a parameter rather than a `Date.now()` call so "missed" is testable.
 */
export function matchesStatus(airdrop: Airdrop, status: string, currentTimeSeconds: number): boolean {
  switch (status) {
    case 'unknown':
      return !airdrop.hasDecoder;
    case 'missed':
      return (
        !!airdrop.hasDecoder
        && !airdrop.claimed
        && typeof airdrop.cutoffTime !== 'undefined'
        && airdrop.cutoffTime !== null
        && airdrop.cutoffTime < currentTimeSeconds
      );
    case 'unclaimed':
      return !!airdrop.hasDecoder && !airdrop.claimed;
    case 'claimed':
      return !!airdrop.claimed;
    default:
      return true;
  }
}

/** The table's rows: flattened, narrowed to the chosen addresses and status, then indexed. */
export function toAirdropRows(
  data: Airdrops,
  addresses: string[],
  status: string,
  currentTimeSeconds: number,
): AirdropWithIndex[] {
  return flattenAirdrops(data, addresses)
    .filter(airdrop => matchesStatus(airdrop, status, currentTimeSeconds))
    .map((value, index) => ({
      ...value,
      amount: value.amount ?? Zero,
      index,
    }));
}

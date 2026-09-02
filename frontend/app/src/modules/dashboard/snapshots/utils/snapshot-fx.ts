import type { BigNumber } from '@rotki/common';

/**
 * Snapshot FX helpers.
 *
 * @remarks
 * Snapshots are stored USD-denominated, so converting into or out of the user's display currency is
 * purely a display and input concern, and must use the historic rate at the snapshot's timestamp
 * rather than today's.
 *
 * These are pure: rate in, value out. Supplying an appropriate historic rate, and
 * short-circuiting when the display currency is already USD, are both the caller's job.
 *
 * @packageDocumentation
 */

/**
 * Converts a USD-denominated value into the user's fiat currency.
 *
 * @param usdValue - the stored USD value
 * @param rate - the USD-to-fiat rate at the relevant timestamp
 */
export function convertUsdToFiat(usdValue: BigNumber, rate: BigNumber): BigNumber {
  return usdValue.multipliedBy(rate);
}

/**
 * Converts a fiat value entered by the user back into USD for storage.
 *
 * @param fiatValue - the value in the user's display currency
 * @param rate - the USD-to-fiat rate at the relevant timestamp
 */
export function convertFiatToUsd(fiatValue: BigNumber, rate: BigNumber): BigNumber {
  return fiatValue.dividedBy(rate);
}

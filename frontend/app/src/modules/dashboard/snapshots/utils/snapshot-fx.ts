import type { BigNumber } from '@rotki/common';

/**
 * Snapshot FX helpers.
 *
 * Snapshots are stored USD-denominated. Converting to/from the user's display
 * currency is purely a display/input concern and must use the historic
 * USD -> fiat rate at the snapshot's timestamp (see #12277), not today's rate.
 *
 * These functions are pure: rate in, value out. The caller is responsible for
 * supplying an appropriate (historic) rate and for short-circuiting when the
 * display currency already is USD.
 */

/**
 * Converts a USD-denominated value into the user's fiat currency.
 *
 * @param usdValue the stored USD value
 * @param rate the USD -> fiat rate at the relevant timestamp
 */
export function convertUsdToFiat(usdValue: BigNumber, rate: BigNumber): BigNumber {
  return usdValue.multipliedBy(rate);
}

/**
 * Converts a fiat value entered by the user back into USD for storage.
 *
 * @param fiatValue the value in the user's display currency
 * @param rate the USD -> fiat rate at the relevant timestamp
 */
export function convertFiatToUsd(fiatValue: BigNumber, rate: BigNumber): BigNumber {
  return fiatValue.dividedBy(rate);
}

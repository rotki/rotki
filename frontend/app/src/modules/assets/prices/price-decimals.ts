import type { BigNumber } from '@rotki/common';

/**
 * How many decimals a price needs to be read rather than only bounded.
 *
 * @remarks
 * Amounts follow the precision setting, three decimals by default, which turns a token priced at
 * 0.0327 into "\< 0.033" and one at 0.0004 into "\< 0.001". A price below 1 gets enough decimals for
 * `significant` digits past its leading zeros, but no more than it has, so 0.5 stays 0.50 rather
 * than padding out to 0.5000. A price of 1 or more keeps `minimum`.
 *
 * @param value - the amount one unit of the asset is worth
 * @param minimum - the decimals every price shows
 * @param significant - the digits a price below 1 shows past its leading zeros
 * @param maximum - the most decimals any price shows
 * @returns the decimals to format the price with
 */
export function priceDecimals(value: BigNumber, minimum = 2, significant = 4, maximum = 12): number {
  const abs = value.abs();
  if (!abs.isFinite() || abs.isZero() || abs.gte(1))
    return minimum;

  const leadingZeros = -Math.floor(Math.log10(abs.toNumber())) - 1;
  const wanted = Math.min(leadingZeros + significant, maximum);
  return Math.max(minimum, Math.min(wanted, abs.decimalPlaces() ?? wanted));
}

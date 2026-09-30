import { type BigNumber, bigNumberify } from '@rotki/common';

/** Beyond this a percentage only says "enormous", and its digits overflow the layout. */
const PERCENT_LIMIT = 1_000_000;

/**
 * A percentage for display, capped at ±1,000,000. A mispriced token turns a snapshot's change or a
 * row's share into a thirty-digit percentage, which `toFormat` prints in full and a plain number
 * prints in exponent notation.
 */
export function formatPercent(value: BigNumber | number, decimals: number): string {
  const percent = typeof value === 'number' ? bigNumberify(value) : value;
  if (percent.abs().isGreaterThan(PERCENT_LIMIT))
    return `${percent.isNegative() ? '<-' : '>'}${bigNumberify(PERCENT_LIMIT).toFormat()}`;
  return percent.toFormat(decimals);
}

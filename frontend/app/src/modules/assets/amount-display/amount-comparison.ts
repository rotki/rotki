import { BigNumber } from '@rotki/common';

interface PrefixSplit {
  /** The leading characters this value has in common with the other one. */
  shared: string;
  /** Everything from the first character that differs. */
  rest: string;
}

/** The largest decimal count among the amounts, so they render at one precision and line up. */
export function sharedDecimals(...amounts: BigNumber[]): number {
  return Math.max(0, ...amounts.map(amount => amount.decimalPlaces() ?? 0));
}

/**
 * Whether two amounts have the same sign and the same number of integer digits.
 *
 * @remarks
 * Only then do their formatted strings line up digit for digit; `12.5` against `1.25` would
 * otherwise appear to share a leading `1`.
 */
export function sameMagnitude(amount: BigNumber, other: BigNumber): boolean {
  const integerDigits = (value: BigNumber): number => value.abs().integerValue(BigNumber.ROUND_DOWN).toFixed().length;
  return amount.isNegative() === other.isNegative() && integerDigits(amount) === integerDigits(other);
}

/**
 * Splits a formatted number where it stops matching another formatted number.
 *
 * @remarks
 * Both strings must come from the same formatter with the same options, so separators line up
 * character for character. Equal strings put everything in `shared`.
 */
export function splitSharedPrefix(value: string, other: string): PrefixSplit {
  let index = 0;
  while (index < value.length && value[index] === other[index])
    index++;
  return { rest: value.slice(index), shared: value.slice(0, index) };
}

/**
 * Whether two values agree on at least their first significant digit.
 *
 * @remarks
 * A shared part made only of signs, zeros and separators means the values differ from their first
 * significant digit, so emphasising the rest would mark the whole number.
 */
export function sharesSignificantDigit({ shared }: PrefixSplit): boolean {
  return /[1-9]/.test(shared);
}

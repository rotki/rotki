import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type Balance, type BigNumber, bigNumberify, Zero } from '@rotki/common';

export function bigNumberifyFromRef(value: MaybeRefOrGetter<string | number>): ComputedRef<BigNumber> {
  return computed(() => {
    const val = toValue(value);
    // Cheap path for a cleared field, which is common enough not to reach it through a throw.
    if (val === '')
      return Zero;

    // bignumber.js rejects anything it cannot parse by throwing, and this runs inside a computed,
    // so an unparsable value would surface as a render-time exception rather than a bad number.
    return bigNumberify(val, Zero);
  });
}

/** The fallback for the parse below: a value bignumber.js accepts but nothing downstream can use. */
const NOT_A_NUMBER = bigNumberify(Number.NaN);

/**
 * Reads a field the user is typing. Without a fallback an unusable value comes back as undefined,
 * so the caller has to answer for it; with one, the result is a number the caller can just use.
 *
 * The callers that pass no fallback are the ones that must not invent a value: a save would
 * otherwise write a nought nobody typed, and a check has to tell "not a number yet" apart from
 * "zero". `''`, `'-'` and `'1.2.3'` are all unusable, as are `'NaN'` and `'Infinity'`, which parse
 * but are no more usable than the ones that throw.
 */
export function parseNumericInput(value: string | number): BigNumber | undefined;

export function parseNumericInput(value: string | number, fallback: BigNumber): BigNumber;

export function parseNumericInput(value: string | number, fallback?: BigNumber): BigNumber | undefined {
  if (typeof value === 'string' && value.trim() === '')
    return fallback;

  const parsed = bigNumberify(value, NOT_A_NUMBER);
  return parsed.isFinite() ? parsed : fallback;
}

export function zeroBalance(): Balance {
  return {
    amount: Zero,
    value: Zero,
  };
}

export function sortDesc(a: BigNumber, b: BigNumber): number {
  return b.minus(a).toNumber();
}

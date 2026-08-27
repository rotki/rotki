import { BigNumber } from 'bignumber.js';
import { markRaw } from 'vue';
import z from 'zod';

markRaw(BigNumber.prototype);

export const Zero = bigNumberify(0);

export const One = bigNumberify(1);

export const NoPrice = bigNumberify(-1);

/**
 * Since bignumber.js 11, invalid input throws instead of producing a NaN
 * BigNumber. That is what we want for values that should already be valid, but
 * unvalidated input (a half-typed amount field, an empty string) is not an
 * error, so those callers pass a fallback to get back the old behaviour at the
 * one place that needs it.
 *
 * The fallback is deliberately not defaulted: silently turning a malformed
 * value into Zero would render as a real balance rather than as a failure.
 */
export function bigNumberify(value: string | number, fallback?: BigNumber): BigNumber {
  if (fallback === undefined)
    return new BigNumber(value);

  try {
    return new BigNumber(value);
  }
  catch {
    return fallback;
  }
}

/**
 * A number or numeric string, parsed to a {@link BigNumber}.
 *
 * @remarks
 * A value `BigNumber` refuses is reported as a zod issue rather than rethrown, because a throw from
 * inside a transform escapes the parse entirely instead of failing it the way every other invalid
 * field does.
 */
export const NumericString = z
  .number()
  .or(z.string())
  .transform((arg, ctx) => {
    try {
      return new BigNumber(arg);
    }
    catch {
      ctx.addIssue({ code: 'custom', message: `${arg} is not a number` });
      return z.NEVER;
    }
  });

export { BigNumber };

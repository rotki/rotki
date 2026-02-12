import { BigNumber } from 'bignumber.js';
import { markRaw } from 'vue';
import z from 'zod/v4';

markRaw(BigNumber.prototype);

export const Zero = bigNumberify(0);

export const One = bigNumberify(1);

export const NoPrice = bigNumberify(-1);

export function bigNumberify(value: string | number): BigNumber {
  return new BigNumber(value);
}

export const NumericString = z
  .number()
  .or(z.string())
  .transform(arg => new BigNumber(arg));

export { BigNumber };

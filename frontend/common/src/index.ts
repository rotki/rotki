import { BigNumber } from "bignumber.js";
import { z } from "zod";

export type Nullable<T> = T | null;

export type AddressIndexed<T> = {
  readonly [address: string]: T
}

export const NumericString = z.string().transform(arg => new BigNumber(arg));

export const Balance = z.object({
  amount: NumericString,
  usdValue: NumericString
})

export type Balance = z.infer<typeof Balance>

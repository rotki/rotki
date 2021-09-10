import { BigNumber } from "bignumber.js";

export type Nullable<T> = T | null;

export type AddressIndexed<T> = {
  readonly [address: string]: T
}

export interface Balance {
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}
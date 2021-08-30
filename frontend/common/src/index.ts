import { BigNumber } from "bignumber.js";

export type Nullable<T> = T | null;

export interface Balance {
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}
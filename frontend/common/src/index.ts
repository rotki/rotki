import { BigNumber } from "bignumber.js";
import { z } from "zod";

export type Nullable<T> = T | null;

export type SemiPartial<T, Ps extends keyof T> = Pick<T, Ps> & Partial<T>;

export type AddressIndexed<T> = {
  readonly [address: string]: T
}

export const NumericString = z.string().transform<BigNumber>(arg => new BigNumber(arg));

export const Balance = z.object({
  amount: NumericString,
  usdValue: NumericString
})

export type Balance = z.infer<typeof Balance>
export const AssetEntry = z.object({
  asset: z.string().nonempty()
});
export const AssetBalance = Balance.merge(AssetEntry);
export type AssetBalance = z.infer<typeof AssetBalance>

const WithPrice = z.object({ usdPrice: z.instanceof(BigNumber)});
export const AssetBalanceWithPrice = AssetBalance.merge(WithPrice)
export type AssetBalanceWithPrice = z.infer<typeof AssetBalanceWithPrice>
export type Diff<T, U> = T extends U ? never : T;

export interface HasBalance {
  readonly balance: Balance;
}

export { BigNumber as BigNumber }

export const PagedResourceParameters = z.object({
  limit: z.union([z.number(), z.undefined()]),
  offset: z.union([z.number(), z.undefined()]),
  orderByAttribute: z.union([z.string(), z.undefined()]),
  ascending: z.union([z.boolean(), z.undefined()]),
})
export type PagedResourceParameters = z.infer<typeof PagedResourceParameters>

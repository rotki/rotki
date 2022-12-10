import { BigNumber } from 'bignumber.js';
import { z } from 'zod';

export type Nullable<T> = T | null;

export type SemiPartial<T, Ps extends keyof T> = Pick<T, Ps> & Partial<T>;

export type AddressIndexed<T> = Readonly<Record<string, T>>;

export const NumericString = z
  .number()
  .or(z.string())
  .transform(arg => new BigNumber(arg));

export const Balance = z.object({
  amount: NumericString,
  usdValue: NumericString
});

export type Balance = z.infer<typeof Balance>;
export const AssetEntry = z.object({
  asset: z.string().nonempty()
});
export const AssetBalance = Balance.merge(AssetEntry);
export type AssetBalance = z.infer<typeof AssetBalance>;

export const Percentage = z.string().refine(
  arg => {
    const number = Number.parseFloat(arg);
    return Number.isFinite(number) && number >= 0 && number <= 100;
  },
  {
    message: 'Percentage must be between 0 and 100'
  }
);

export type Percentage = z.infer<typeof Percentage>;

const WithPrice = z.object({ usdPrice: NumericString });
export const AssetBalanceWithPrice = AssetBalance.merge(WithPrice);
export type AssetBalanceWithPrice = z.infer<typeof AssetBalanceWithPrice>;
export type Diff<T, U> = T extends U ? never : T;

export interface HasBalance {
  readonly balance: Balance;
}

export { BigNumber as BigNumber };

export const onlyIfTruthy = <T>(value: T): T | undefined =>
  value ? value : undefined;

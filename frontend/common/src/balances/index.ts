import z from 'zod';
import { NumericString } from '../numbers';

export const Balance = z.object({
  amount: NumericString,
  usdValue: NumericString,
});

export type Balance = z.infer<typeof Balance>;

export const AssetEntry = z.object({
  asset: z.string().min(1),
});

export const AssetBalance = Balance.merge(AssetEntry);

export type AssetBalance = z.infer<typeof AssetBalance>;

export const Percentage = z.string().refine((arg) => {
  const number = Number.parseFloat(arg);
  return Number.isFinite(number) && number >= 0 && number <= 100;
}, {
  message: 'Percentage must be between 0 and 100',
});

const WithPrice = z.object({ usdPrice: NumericString });

const AssetBalanceWithPriceBeforeBreakdown = AssetBalance.merge(WithPrice);
const AssetBalanceWithPrice = AssetBalanceWithPriceBeforeBreakdown.extend({
  breakdown: z.array(AssetBalanceWithPriceBeforeBreakdown).optional(),
});

export type AssetBalanceWithPrice = z.infer<typeof AssetBalanceWithPrice>;

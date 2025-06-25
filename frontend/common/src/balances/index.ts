import z from 'zod/v4';
import { NumericString } from '../numbers';

export const Balance = z.object({
  amount: NumericString,
  usdValue: NumericString,
});

export type Balance = z.infer<typeof Balance>;

export const AssetEntry = z.object({
  asset: z.string().min(1),
});

export const AssetBalance = z.object({
  ...Balance.shape,
  ...AssetEntry.shape,
});

export type AssetBalance = z.infer<typeof AssetBalance>;

export const Percentage = z.string().refine((arg) => {
  const number = Number.parseFloat(arg);
  return Number.isFinite(number) && number >= 0 && number <= 100;
}, {
  message: 'Percentage must be between 0 and 100',
});

const ProtocolBalanceSchema = Balance.extend({
  containsManual: z.boolean().optional(),
  protocol: z.string(),
});

const BaseAssetBalanceSchema = z.object({
  ...AssetBalance.shape,
  usdPrice: NumericString,
});

const BreakdownSchema = BaseAssetBalanceSchema.extend({
  perProtocol: z.array(ProtocolBalanceSchema).optional(),
});

export type ProtocolBalance = z.infer<typeof ProtocolBalanceSchema>;

const AssetBalanceWithPrice = BaseAssetBalanceSchema.extend({
  breakdown: z.array(BreakdownSchema).optional(),
  perProtocol: z.array(ProtocolBalanceSchema).optional(),
});

export type AssetBalanceWithPrice = z.infer<typeof AssetBalanceWithPrice>;

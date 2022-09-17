import { NumericString } from '@rotki/common';
import { z } from 'zod';
import { BalanceType } from '@/services/balances/types';
import { TradeLocation } from '@/types/history/trade-location';

export const ManualBalance = z.object({
  id: z.number().positive(),
  asset: z.string(),
  label: z.string(),
  amount: NumericString,
  location: TradeLocation,
  tags: z.array(z.string()).nullable(),
  balanceType: z.nativeEnum(BalanceType)
});
export type ManualBalance = z.infer<typeof ManualBalance>;
export const ManualBalanceWithValue = ManualBalance.merge(
  z.object({ usdValue: NumericString })
);
export type ManualBalanceWithValue = z.infer<typeof ManualBalanceWithValue>;
export const ManualBalances = z.object({
  balances: z.array(ManualBalanceWithValue)
});
export type ManualBalances = z.infer<typeof ManualBalances>;

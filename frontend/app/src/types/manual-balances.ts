import type { PaginationRequestPayload } from '@/types/common';
import { NumericString } from '@rotki/common';
import { z } from 'zod/v4';
import { BalanceType } from '@/types/balances';

const RawManualBalance = z.object({
  amount: NumericString,
  asset: z.string(),
  assetIsMissing: z.boolean().optional(),
  balanceType: z.enum(BalanceType),
  label: z.string(),
  location: z.string(),
  tags: z.array(z.string()).nullable(),
});

export type RawManualBalance = z.infer<typeof RawManualBalance>;

export const ManualBalance = z.object({
  identifier: z.number().positive(),
  ...RawManualBalance.shape,
});

export type ManualBalance = z.infer<typeof ManualBalance>;

export const ManualBalanceWithValue = z.object({
  ...ManualBalance.shape,
  value: NumericString,
});

export type ManualBalanceWithValue = z.infer<typeof ManualBalanceWithValue>;

export const ManualBalances = z.object({
  balances: z.array(ManualBalanceWithValue),
});

export type ManualBalances = z.infer<typeof ManualBalances>;

const ManualBalanceWithPrice = z.object({
  ...ManualBalanceWithValue.shape,
  usdPrice: NumericString.optional(),
});

export type ManualBalanceWithPrice = z.infer<typeof ManualBalanceWithPrice>;

export interface ManualBalanceRequestPayload extends PaginationRequestPayload<ManualBalanceWithValue> {
  readonly tags?: string[];
  readonly label?: string;
  readonly asset?: string;
  readonly location?: string;
}

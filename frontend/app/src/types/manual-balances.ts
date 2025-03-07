import type { PaginationRequestPayload } from '@/types/common';
import { BalanceType } from '@/types/balances';
import { NumericString } from '@rotki/common';
import { z } from 'zod';

const RawManualBalance = z.object({
  amount: NumericString,
  asset: z.string(),
  assetIsMissing: z.boolean().optional(),
  balanceType: z.nativeEnum(BalanceType),
  label: z.string(),
  location: z.string(),
  tags: z.array(z.string()).nullable(),
});

export type RawManualBalance = z.infer<typeof RawManualBalance>;

export const ManualBalance = z
  .object({
    identifier: z.number().positive(),
  })
  .merge(RawManualBalance);

export type ManualBalance = z.infer<typeof ManualBalance>;

export const ManualBalanceWithValue = ManualBalance.merge(z.object({ usdValue: NumericString }));

export type ManualBalanceWithValue = z.infer<typeof ManualBalanceWithValue>;

export const ManualBalances = z.object({
  balances: z.array(ManualBalanceWithValue),
});

export type ManualBalances = z.infer<typeof ManualBalances>;

const ManualBalanceWithPrice = ManualBalanceWithValue.merge(z.object({ usdPrice: NumericString.optional() }));

export type ManualBalanceWithPrice = z.infer<typeof ManualBalanceWithPrice>;

export interface ManualBalanceRequestPayload extends PaginationRequestPayload<ManualBalanceWithValue> {
  readonly tags?: string[];
  readonly label?: string;
  readonly asset?: string;
  readonly location?: string;
}

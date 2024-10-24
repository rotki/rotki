import { type BigNumber, NumericString } from '@rotki/common';
import { z } from 'zod';
import { BalanceType } from '@/types/balances';
import type { PaginationRequestPayload } from '@/types/common';

const RawManualBalance = z.object({
  asset: z.string(),
  label: z.string(),
  amount: NumericString,
  location: z.string(),
  tags: z.array(z.string()).nullable(),
  balanceType: z.nativeEnum(BalanceType),
});

export type RawManualBalance = z.infer<typeof RawManualBalance>;

export const ManualBalance = z
  .object({
    identifier: z.number().positive(),
  })
  .merge(RawManualBalance);

export type ManualBalance = z.infer<typeof ManualBalance>;

export const ManualBalanceWithValue = ManualBalance.merge(z.object({
  value: NumericString.optional().default(0),
}));

export type ManualBalanceWithValue = z.infer<typeof ManualBalanceWithValue>;

export const ManualBalances = z.object({
  balances: z.array(ManualBalanceWithValue),
});

export type ManualBalances = z.infer<typeof ManualBalances>;

export interface ManualBalanceWithPrice extends ManualBalanceWithValue {
  price?: BigNumber;
};

export interface ManualBalanceRequestPayload extends PaginationRequestPayload<ManualBalanceWithValue> {
  readonly tags?: string[];
  readonly label?: string;
  readonly asset?: string;
  readonly location?: string;
}

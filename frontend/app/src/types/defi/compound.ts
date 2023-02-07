import { Balance } from '@rotki/common';
import { z } from 'zod';
import {
  DEFI_EVENT_BORROW,
  DEFI_EVENT_LIQUIDATION,
  DEFI_EVENT_REPAY
} from '@/types/defi/events';
import { type Collateral, type CollateralizedLoan } from '@/types/defi/index';

const CompoundReward = z.object({
  balance: Balance
});

const CompoundRewards = z.record(CompoundReward);

const CompoundLending = z.object({
  balance: Balance,
  apy: z.string().nullable()
});

const CompoundLendingEntries = z.record(CompoundLending);

const CompoundBorrowing = z.object({
  balance: Balance,
  apy: z.string().nullable()
});

const CompoundBorrowingEntries = z.record(CompoundBorrowing);

const CompoundBalance = z.object({
  rewards: CompoundRewards,
  lending: CompoundLendingEntries,
  borrowing: CompoundBorrowingEntries
});

export const CompoundBalances = z.record(CompoundBalance);

export type CompoundBalances = z.infer<typeof CompoundBalances>;

export const COMPOUND_EVENT_TYPES = [
  'mint',
  'redeem',
  DEFI_EVENT_BORROW,
  DEFI_EVENT_REPAY,
  DEFI_EVENT_LIQUIDATION,
  'comp'
] as const;

const CompoundEventType = z.enum(COMPOUND_EVENT_TYPES);
export type CompoundEventType = z.infer<typeof CompoundEventType>;

const CompoundEvent = z.object({
  eventType: CompoundEventType,
  address: z.string(),
  blockNumber: z.number(),
  timestamp: z.number(),
  asset: z.string(),
  toAsset: z.string().nullable(),
  value: Balance,
  toValue: Balance.nullable(),
  realizedPnl: Balance.nullable(),
  txHash: z.string(),
  logIndex: z.number()
});

type CompoundEvent = z.infer<typeof CompoundEvent>;

const CompoundAssetProfitAndLoss = z.record(Balance);

const CompoundProfitAndLoss = z.record(CompoundAssetProfitAndLoss);

export type CompoundProfitAndLoss = z.infer<typeof CompoundProfitAndLoss>;

export const CompoundHistory = z.object({
  events: z.array(CompoundEvent),
  interestProfit: CompoundProfitAndLoss,
  debtLoss: CompoundProfitAndLoss,
  rewards: CompoundProfitAndLoss,
  liquidationProfit: CompoundProfitAndLoss
});

export type CompoundHistory = z.infer<typeof CompoundHistory>;

type IdedCompoundEvent = CompoundEvent & { id: string };

export interface CompoundLoan extends CollateralizedLoan<Collateral[]> {
  readonly apy: string;
  readonly events: IdedCompoundEvent[];
}

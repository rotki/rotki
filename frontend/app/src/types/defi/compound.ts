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

const CompoundAssetProfitAndLoss = z.record(Balance);

const CompoundProfitAndLoss = z.record(CompoundAssetProfitAndLoss);

export type CompoundProfitAndLoss = z.infer<typeof CompoundProfitAndLoss>;

export const CompoundHistory = z.object({
  interestProfit: CompoundProfitAndLoss,
  debtLoss: CompoundProfitAndLoss,
  rewards: CompoundProfitAndLoss,
  liquidationProfit: CompoundProfitAndLoss
});

export type CompoundHistory = z.infer<typeof CompoundHistory>;

export interface CompoundLoan extends CollateralizedLoan<Collateral[]> {
  readonly apy: string;
}

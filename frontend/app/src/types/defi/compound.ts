import { Balance } from '@rotki/common';
import { z } from 'zod';
import type { Collateral, CollateralizedLoan } from '@/types/defi/index';

const CompoundReward = z.object({
  balance: Balance,
});

const CompoundRewards = z.record(CompoundReward);

const CompoundLending = z.object({
  apy: z.string().nullable(),
  balance: Balance,
});

const CompoundLendingEntries = z.record(CompoundLending);

const CompoundBorrowing = z.object({
  apy: z.string().nullable(),
  balance: Balance,
});

const CompoundBorrowingEntries = z.record(CompoundBorrowing);

const CompoundBalance = z.object({
  borrowing: CompoundBorrowingEntries.optional().default({}),
  lending: CompoundLendingEntries.optional().default({}),
  rewards: CompoundRewards.optional().default({}),
});

export const CompoundBalances = z.record(CompoundBalance);

export type CompoundBalances = z.infer<typeof CompoundBalances>;

const CompoundAssetProfitAndLoss = z.record(Balance);

const CompoundProfitAndLoss = z.record(CompoundAssetProfitAndLoss);

export type CompoundProfitAndLoss = z.infer<typeof CompoundProfitAndLoss>;

export const CompoundStats = z.object({
  debtLoss: CompoundProfitAndLoss,
  interestProfit: CompoundProfitAndLoss,
  liquidationProfit: CompoundProfitAndLoss,
  rewards: CompoundProfitAndLoss,
});

export type CompoundStats = z.infer<typeof CompoundStats>;

export interface CompoundLoan extends CollateralizedLoan<Collateral[]> {
  readonly apy: string;
}

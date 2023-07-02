import { Balance } from '@rotki/common';
import { z } from 'zod';
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

const CompoundAssetProfitAndLoss = z.record(Balance);

const CompoundProfitAndLoss = z.record(CompoundAssetProfitAndLoss);

export type CompoundProfitAndLoss = z.infer<typeof CompoundProfitAndLoss>;

export const CompoundStats = z.object({
  interestProfit: CompoundProfitAndLoss,
  debtLoss: CompoundProfitAndLoss,
  rewards: CompoundProfitAndLoss,
  liquidationProfit: CompoundProfitAndLoss
});

export type CompoundStats = z.infer<typeof CompoundStats>;

export interface CompoundLoan extends CollateralizedLoan<Collateral[]> {
  readonly apy: string;
}

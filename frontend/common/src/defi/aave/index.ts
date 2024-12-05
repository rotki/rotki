import { z } from 'zod';
import { Balance } from '../../balances';

export interface AaveBorrowingRates {
  readonly stableApr: string;
  readonly variableApr: string;
}

const AaveBorrowingAsset = z.object({
  balance: Balance,
  stableApr: z.string(),
  variableApr: z.string(),
});

const AaveLendingAsset = z.object({
  apy: z.string(),
  balance: Balance,
});

const AaveBorrowing = z.record(AaveBorrowingAsset);

const AaveLending = z.record(AaveLendingAsset);

export type AaveLending = z.infer<typeof AaveLending>;

const AaveBalance = z.object({
  borrowing: AaveBorrowing,
  lending: AaveLending,
});

export const AaveBalances = z.record(AaveBalance);

export type AaveBalances = z.infer<typeof AaveBalances>;
const AaveHistoryTotal = z.record(Balance);

export type AaveHistoryTotal = z.infer<typeof AaveHistoryTotal>;

const AaveAccountingHistory = z.object({
  totalEarnedInterest: AaveHistoryTotal,
  totalEarnedLiquidations: AaveHistoryTotal,
  totalLost: AaveHistoryTotal,
});

export const AaveHistory = z.record(AaveAccountingHistory);

export type AaveHistory = z.infer<typeof AaveHistory>;

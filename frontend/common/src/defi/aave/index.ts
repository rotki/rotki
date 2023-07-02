import { z } from 'zod';
import { Balance } from '../../index';

export interface AaveBorrowingRates {
  readonly stableApr: string;
  readonly variableApr: string;
}

const AaveBorrowingAsset = z.object({
  balance: Balance,
  stableApr: z.string(),
  variableApr: z.string()
});

const AaveLendingAsset = z.object({
  balance: Balance,
  apy: z.string()
});

const AaveBorrowing = z.record(AaveBorrowingAsset);

const AaveLending = z.record(AaveLendingAsset);

export type AaveLending = z.infer<typeof AaveLending>;

const AaveBalance = z.object({
  lending: AaveLending,
  borrowing: AaveBorrowing
});

export const AaveBalances = z.record(AaveBalance);

export type AaveBalances = z.infer<typeof AaveBalances>;
const AaveHistoryTotal = z.record(Balance);

export type AaveHistoryTotal = z.infer<typeof AaveHistoryTotal>;

const AaveAccountingHistory = z.object({
  totalEarnedInterest: AaveHistoryTotal,
  totalEarnedLiquidations: AaveHistoryTotal,
  totalLost: AaveHistoryTotal
});

export const AaveHistory = z.record(AaveAccountingHistory);

export type AaveHistory = z.infer<typeof AaveHistory>;

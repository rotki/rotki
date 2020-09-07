import { AaveEventType } from '@/services/defi/types';
import { Balance, HasBalance } from '@/services/types-api';

export interface AaveBorrowingRates {
  readonly stableApr: string;
  readonly variableApr: string;
}

interface AaveBorrowingAsset extends HasBalance, AaveBorrowingRates {}

interface AaveLendingAsset extends HasBalance {
  readonly apy: string;
}

interface AaveBorrowing {
  readonly [asset: string]: AaveBorrowingAsset;
}

interface AaveLending {
  readonly [asset: string]: AaveLendingAsset;
}

interface AaveBalance {
  readonly lending: AaveLending;
  readonly borrowing: AaveBorrowing;
}

export interface AaveBalances {
  readonly [address: string]: AaveBalance;
}

interface AaveHistoryEvents {
  eventType: AaveEventType;
  asset: string;
  value: Balance;
  blockNumber: number;
  timestamp: number;
  txHash: string;
}

interface AaveHistoryTotalEarned {
  readonly [asset: string]: Balance;
}

interface AaveAccountHistory {
  readonly events: AaveHistoryEvents[];
  readonly totalEarned: AaveHistoryTotalEarned;
}

export interface AaveHistory {
  readonly [address: string]: AaveAccountHistory;
}

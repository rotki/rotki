import { default as BigNumber } from 'bignumber.js';
import {
  DEFI_EVENT_BORROW,
  DEFI_EVENT_LIQUIDATION,
  DEFI_EVENT_REPAY
} from '@/services/defi/consts';
import { AaveEventType } from '@/services/defi/types';
import { AAVE_BORROW_RATE } from '@/services/defi/types/consts';
import { Balance, HasBalance } from '@/services/types-api';
import { Diff } from '@/types';

type AaveBorrowRate = typeof AAVE_BORROW_RATE[number];

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

interface AaveBaseEvent {
  readonly eventType: AaveEventType;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly txHash: string;
  readonly logIndex: number;
}

interface AaveEvent extends AaveBaseEvent {
  readonly eventType: Diff<AaveEventType, typeof DEFI_EVENT_LIQUIDATION>;
  readonly asset: string;
  readonly value: Balance;
}

interface AaveLiquidationEvent extends AaveBaseEvent {
  readonly eventType: typeof DEFI_EVENT_LIQUIDATION;
  readonly collateralAsset: string;
  readonly collateralBalance: Balance;
  readonly principalAsset: string;
  readonly principalBalance: Balance;
}

interface AaveRepayEvent extends AaveEvent {
  readonly eventType: typeof DEFI_EVENT_REPAY;
  readonly fee: Balance;
}

interface AaveBorrowEvent extends AaveEvent {
  readonly eventType: typeof DEFI_EVENT_BORROW;
  readonly borrowRateMode: AaveBorrowRate;
  readonly borrowRate: BigNumber;
  readonly accruedBorrowInterest: BigNumber;
}

type AaveBorrowingEvent =
  | AaveLiquidationEvent
  | AaveRepayEvent
  | AaveBorrowEvent;

export type AaveHistoryEvents = AaveEvent | AaveBorrowingEvent;

export interface AaveHistoryTotal {
  readonly [asset: string]: Balance;
}

interface AaveAccountHistory {
  readonly events: AaveHistoryEvents[];
  readonly totalEarned: AaveHistoryTotal;
  readonly totalLost: AaveHistoryTotal;
}

export interface AaveHistory {
  readonly [address: string]: AaveAccountHistory;
}

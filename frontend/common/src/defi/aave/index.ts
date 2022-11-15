import { BigNumber } from "bignumber.js";
import { Balance, Diff, HasBalance } from "../../index";

enum AaveBorrowRate {
  STABLE = "stable",
  VARIABLE = "variable"
}

export interface AaveBorrowingRates {
  readonly stableApr: string;
  readonly variableApr: string;
}

interface AaveBorrowingAsset extends HasBalance, AaveBorrowingRates {
}

interface AaveLendingAsset extends HasBalance {
  readonly apy: string;
}

type AaveBorrowing = Readonly<Record<string, AaveBorrowingAsset>>;

export type AaveLending = Readonly<Record<string, AaveLendingAsset>>;

interface AaveBalance {
  readonly lending: AaveLending;
  readonly borrowing: AaveBorrowing;
}

export type AaveBalances = Readonly<Record<string, AaveBalance>>;

export enum AaveBorrowingEventType {
  REPAY = "repay",
  LIQUIDATION = "liquidation",
  BORROW = "borrow",
}

export enum AaveLendingEventType {
  DEPOSIT = "deposit",
  INTEREST = "interest",
  WITHDRAWAL = "withdrawal",
}

export type AaveEventType = AaveLendingEventType | AaveBorrowingEventType;

interface AaveBaseEvent {
  readonly eventType: AaveEventType;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly txHash: string;
  readonly logIndex: number;
}

export interface AaveEvent extends AaveBaseEvent {
  readonly eventType: Diff<AaveEventType, typeof AaveBorrowingEventType.LIQUIDATION>;
  readonly asset: string;
  readonly atoken: string;
  readonly value: Balance;
}

export interface AaveLiquidationEvent extends AaveBaseEvent {
  readonly eventType: typeof AaveBorrowingEventType.LIQUIDATION;
  readonly collateralAsset: string;
  readonly collateralBalance: Balance;
  readonly principalAsset: string;
  readonly principalBalance: Balance;
}

export function isAaveLiquidationEvent(value: AaveHistoryEvents): value is AaveLiquidationEvent {
  return value.eventType === AaveBorrowingEventType.LIQUIDATION;
}

interface AaveRepayEvent extends AaveEvent {
  readonly eventType: typeof AaveBorrowingEventType.REPAY;
  readonly fee: Balance;
}

interface AaveBorrowEvent extends AaveEvent {
  readonly eventType: typeof AaveBorrowingEventType.BORROW;
  readonly borrowRateMode: AaveBorrowRate;
  readonly borrowRate: BigNumber;
  readonly accruedBorrowInterest: BigNumber;
}

export type AaveBorrowingEvent =
  | AaveLiquidationEvent
  | AaveRepayEvent
  | AaveBorrowEvent;
export type AaveHistoryEvents = AaveEvent | AaveBorrowingEvent;

export type AaveHistoryTotal = Readonly<Record<string, Balance>>;

interface AaveAccountHistory {
  readonly events: AaveHistoryEvents[];
  readonly totalEarnedInterest: AaveHistoryTotal;
  readonly totalEarnedLiquidations: AaveHistoryTotal;
  readonly totalLost: AaveHistoryTotal;
}

export type AaveHistory = Readonly<Record<string, AaveAccountHistory>>;
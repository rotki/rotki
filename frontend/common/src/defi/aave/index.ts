import { z } from 'zod';
import { Balance, NumericString } from '../../index';

enum AaveBorrowRate {
  STABLE = 'stable',
  VARIABLE = 'variable'
}

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

export enum AaveBorrowingEventType {
  REPAY = 'repay',
  LIQUIDATION = 'liquidation',
  BORROW = 'borrow'
}

export enum AaveLendingEventType {
  DEPOSIT = 'deposit',
  INTEREST = 'interest',
  WITHDRAWAL = 'withdrawal'
}

export type AaveEventType = AaveLendingEventType | AaveBorrowingEventType;

const AaveEventType = z
  .nativeEnum(AaveLendingEventType)
  .or(z.nativeEnum(AaveBorrowingEventType));

const AaveBaseEvent = z.object({
  eventType: AaveEventType,
  blockNumber: z.number(),
  timestamp: z.number(),
  txHash: z.string(),
  logIndex: z.number()
});

const AaveEvent = z
  .object({
    asset: z.string(),
    value: Balance
  })
  .merge(AaveBaseEvent);

const BaseAaveLendingEvent = z
  .object({
    eventType: z.nativeEnum(AaveLendingEventType)
  })
  .merge(AaveEvent);

const AaveLendingInterestEvent = z
  .object({
    eventType: z.literal(AaveLendingEventType.INTEREST)
  })
  .merge(BaseAaveLendingEvent);

const AaveMovementEvent = z
  .object({
    eventType: z
      .literal(AaveLendingEventType.DEPOSIT)
      .or(z.literal(AaveLendingEventType.WITHDRAWAL)),
    atoken: z.string()
  })
  .merge(BaseAaveLendingEvent);

const AaveLendingEvent = AaveLendingInterestEvent.or(AaveMovementEvent);

export type AaveLendingEvent = z.infer<typeof AaveLendingEvent>;

export const AaveLiquidationEvent = z
  .object({
    eventType: z.literal(AaveBorrowingEventType.LIQUIDATION),
    collateralBalance: Balance,
    collateralAsset: z.string(),
    principalAsset: z.string(),
    principalBalance: Balance
  })
  .merge(AaveBaseEvent);

export type AaveLiquidationEvent = z.infer<typeof AaveLiquidationEvent>;

export function isAaveLiquidationEvent(
  value: AaveHistoryEvents
): value is AaveLiquidationEvent {
  return value.eventType === AaveBorrowingEventType.LIQUIDATION;
}

const AaveRepayEvent = z
  .object({
    eventType: z.literal(AaveBorrowingEventType.REPAY),
    fee: Balance
  })
  .merge(AaveEvent);

const AaveBorrowEvent = z
  .object({
    eventType: z.literal(AaveBorrowingEventType.BORROW),
    borrowRateMode: z.nativeEnum(AaveBorrowRate),
    borrowRate: NumericString,
    accruedBorrowInterest: NumericString
  })
  .merge(AaveEvent);

const AaveBorrowingEvent =
  AaveLiquidationEvent.or(AaveRepayEvent).or(AaveBorrowEvent);
export type AaveBorrowingEvent = z.infer<typeof AaveBorrowingEvent>;
const AaveHistoryEvents = AaveBorrowingEvent.or(AaveLendingEvent);
export type AaveHistoryEvents = z.infer<typeof AaveHistoryEvents>;

const AaveHistoryTotal = z.record(Balance);

export type AaveHistoryTotal = z.infer<typeof AaveHistoryTotal>;

const AaveAccountingHistory = z.object({
  totalEarnedInterest: AaveHistoryTotal,
  totalEarnedLiquidations: AaveHistoryTotal,
  totalLost: AaveHistoryTotal
});

export const AaveHistory = z.record(AaveAccountingHistory);

export type AaveHistory = z.infer<typeof AaveHistory>;

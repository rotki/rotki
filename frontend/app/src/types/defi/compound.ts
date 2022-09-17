import { Balance, HasBalance } from '@rotki/common';
import {
  DEFI_EVENT_BORROW,
  DEFI_EVENT_LIQUIDATION,
  DEFI_EVENT_REPAY
} from '@/services/defi/events';
import { Collateral, CollateralizedLoan } from '@/types/defi/index';

interface CompoundReward extends HasBalance {}

interface CompoundRewards {
  readonly [asset: string]: CompoundReward;
}

interface CompoundLending extends HasBalance {
  readonly apy: string | null;
}

interface CompoundLendingEntries {
  readonly [asset: string]: CompoundLending;
}

interface CompoundBorrowing extends HasBalance {
  readonly apy: string;
}

interface CompoundBorrowingEntries {
  readonly [asset: string]: CompoundBorrowing;
}

interface CompoundBalance {
  readonly rewards: CompoundRewards;
  readonly lending: CompoundLendingEntries;
  readonly borrowing: CompoundBorrowingEntries;
}

export interface CompoundBalances {
  readonly [address: string]: CompoundBalance;
}

export const COMPOUND_EVENT_TYPES = [
  'mint',
  'redeem',
  DEFI_EVENT_BORROW,
  DEFI_EVENT_REPAY,
  DEFI_EVENT_LIQUIDATION,
  'comp'
] as const;
export type CompoundEventType = typeof COMPOUND_EVENT_TYPES[number];

interface CompoundEvent {
  readonly eventType: CompoundEventType;
  readonly address: string;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly asset: string;
  readonly toAsset?: string;
  readonly value: Balance;
  readonly toValue?: Balance;
  readonly realizedPnl?: Balance;
  readonly txHash: string;
  readonly logIndex: number;
}

interface CompoundAssetProfitAndLoss {
  readonly [asset: string]: Balance;
}

export interface CompoundProfitAndLoss {
  readonly [address: string]: CompoundAssetProfitAndLoss;
}

export interface CompoundHistory {
  readonly events: CompoundEvent[];
  readonly interestProfit: CompoundProfitAndLoss;
  readonly debtLoss: CompoundProfitAndLoss;
  readonly rewards: CompoundProfitAndLoss;
  readonly liquidationProfit: CompoundProfitAndLoss;
}

type IdedCompoundEvent = CompoundEvent & { id: string };

export interface CompoundLoan extends CollateralizedLoan<Collateral<string>[]> {
  readonly apy: string;
  readonly events: IdedCompoundEvent[];
}

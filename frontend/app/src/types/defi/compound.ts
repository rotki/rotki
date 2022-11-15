import { Balance, HasBalance } from '@rotki/common';
import {
  DEFI_EVENT_BORROW,
  DEFI_EVENT_LIQUIDATION,
  DEFI_EVENT_REPAY
} from '@/services/defi/events';
import { Collateral, CollateralizedLoan } from '@/types/defi/index';

interface CompoundReward extends HasBalance {}

type CompoundRewards = Readonly<Record<string, CompoundReward>>;

interface CompoundLending extends HasBalance {
  readonly apy: string | null;
}

type CompoundLendingEntries = Readonly<Record<string, CompoundLending>>;

interface CompoundBorrowing extends HasBalance {
  readonly apy: string;
}

type CompoundBorrowingEntries = Readonly<Record<string, CompoundBorrowing>>;

interface CompoundBalance {
  readonly rewards: CompoundRewards;
  readonly lending: CompoundLendingEntries;
  readonly borrowing: CompoundBorrowingEntries;
}

export type CompoundBalances = Readonly<Record<string, CompoundBalance>>;

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

type CompoundAssetProfitAndLoss = Readonly<Record<string, Balance>>;

export type CompoundProfitAndLoss = Readonly<
  Record<string, CompoundAssetProfitAndLoss>
>;

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

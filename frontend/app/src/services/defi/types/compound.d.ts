import { Balance, HasBalance } from '@rotki/common';
import { COMPOUND_EVENT_TYPES } from '@/services/defi/consts';
import { Collateral, CollateralizedLoan } from '@/store/defi/types';

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

interface CompoundProfitAndLoss {
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

import { COMPOUND_EVENT_TYPES } from '@/services/defi/consts';
import { Balance, HasBalance } from '@/services/types-api';

interface CompoundReward extends HasBalance {}

interface CompoundRewards {
  readonly [asset: string]: CompoundReward;
}

interface CompoundLending extends HasBalance {
  readonly apy: string;
}

interface CompoundLendingEntries {
  readonly [asset: string]: CompoundLending;
}

interface CompoundBorrowing extends HasBalance {
  readonly apr: string;
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

type CompoundEventType = typeof COMPOUND_EVENT_TYPES[number];

interface CompoundEvent {
  readonly eventType: CompoundEventType;
  readonly address: string;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly asset: string;
  readonly toAsset?: string;
  readonly value: Balance;
  readonly toValue?: Balance;
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
  readonly profitAndLoss: CompoundProfitAndLoss;
}

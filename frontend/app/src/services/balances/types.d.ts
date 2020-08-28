import { default as BigNumber } from 'bignumber.js';
import { exchanges } from '@/data/defaults';
import { TradeLocation } from '@/services/trades/types';

export type SupportedExchange = typeof exchanges[number];

export type MovementCategory = 'deposit' | 'withdrawal';

export interface AssetMovement {
  readonly identifier: string;
  readonly location: TradeLocation;
  readonly category: MovementCategory;
  readonly address: string;
  readonly transactionId: string;
  readonly timestamp: number;
  readonly asset: string;
  readonly amount: BigNumber;
  readonly feeAsset: string;
  readonly fee: BigNumber;
  readonly link: string;
}

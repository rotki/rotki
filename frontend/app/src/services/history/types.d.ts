import { default as BigNumber } from 'bignumber.js';
import {
  SupportedExchange,
  SupportedTradeLocation
} from '@/services/balances/types';
import { TradeEntry } from '@/store/history/types';

export type TradeType = 'buy' | 'sell';

export interface Trade {
  readonly tradeId: string;
  readonly timestamp: number;
  readonly location: TradeLocation;
  readonly pair: string;
  readonly tradeType: TradeType;
  readonly amount: BigNumber;
  readonly rate: BigNumber;
  readonly fee: BigNumber;
  readonly feeCurrency: string;
  readonly link: string;
  readonly notes: string;
}

export type NewTrade = Omit<Trade, 'tradeId' | 'ignoredInAccounting'>;

export interface TradeUpdate {
  readonly trade: TradeEntry;
  readonly oldTradeId: string;
}

export type TradeLocation = SupportedExchange | SupportedTradeLocation;

type MovementCategory = 'deposit' | 'withdrawal';

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

export interface EthTransaction {
  readonly txHash: string;
  readonly timestamp: number;
  readonly blockNumber: number;
  readonly fromAddress: string;
  readonly toAddress: string;
  readonly value: BigNumber;
  readonly gas: BigNumber;
  readonly gasPrice: BigNumber;
  readonly gasUsed: BigNumber;
  readonly inputData: string;
  readonly nonce: number;
}

export interface LedgerActionResult {
  readonly identifier: number;
}

import { default as BigNumber } from 'bignumber.js';
import { SupportedExchange } from '@/services/balances/types';

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

export type NewTrade = Omit<Trade, 'tradeId'>;

export interface TradeUpdate {
  readonly trade: Trade;
  readonly oldTradeId: string;
}

export type TradeLocation =
  | SupportedExchange
  | 'ethereum'
  | 'bitcoin'
  | 'external';

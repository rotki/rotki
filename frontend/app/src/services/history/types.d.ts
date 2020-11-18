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
  | 'external'
  | 'uniswap';

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

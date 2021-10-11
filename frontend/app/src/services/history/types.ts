import { NumericString } from '@rotki/common';
import { default as BigNumber } from 'bignumber.js';
import { z } from 'zod';
import {
  SupportedExchange,
  SupportedTradeLocation
} from '@/services/balances/types';
import { TradeEntry } from '@/store/history/types';
import { Nullable } from '@/types';

export type TradeType = 'buy' | 'sell';

export interface Trade {
  readonly tradeId: string;
  readonly timestamp: number;
  readonly location: TradeLocation;
  readonly baseAsset: string;
  readonly quoteAsset: string;
  readonly tradeType: TradeType;
  readonly amount: BigNumber;
  readonly rate: BigNumber;
  readonly fee?: Nullable<BigNumber>;
  readonly feeCurrency?: Nullable<string>;
  readonly link?: Nullable<string>;
  readonly notes?: Nullable<string>;
}

export type NewTrade = Omit<Trade, 'tradeId' | 'ignoredInAccounting'>;

export interface TradeUpdate {
  readonly trade: TradeEntry;
  readonly oldTradeId: string;
}

export type TradeLocation =
  | SupportedExchange
  | SupportedTradeLocation
  | 'gitcoin';

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

export const EthTransaction = z.object({
  txHash: z.string(),
  timestamp: z.number(),
  blockNumber: z.number(),
  fromAddress: z.string(),
  toAddress: z.string(),
  value: NumericString,
  gas: NumericString,
  gasPrice: NumericString,
  gasUsed: NumericString,
  inputData: z.string(),
  nonce: z.number()
});

export type EthTransaction = z.infer<typeof EthTransaction>;

const EthTransactionWithMeta = z.object({
  entry: EthTransaction,
  ignoredInAccounting: z.boolean()
});

export type EthTransactionWithMeta = z.infer<typeof EthTransactionWithMeta>;

export const Transactions = z.object({
  entries: z.array(EthTransactionWithMeta),
  entriesFound: z.number(),
  entriesLimit: z.number(),
  entriesTotal: z.number()
});

export type Transactions = z.infer<typeof Transactions>;

export interface LedgerActionResult {
  readonly identifier: number;
}

export type TransactionRequestPayload = {
  readonly limit: number;
  readonly offset: number;
  readonly orderByAttribute: keyof EthTransaction;
  readonly ascending: boolean;
  readonly fromTimestamp?: number;
  readonly toTimestamp?: number;
  readonly onlyCache?: boolean;
  readonly address?: string;
};

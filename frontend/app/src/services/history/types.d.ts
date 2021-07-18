import { default as BigNumber } from 'bignumber.js';
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

interface GitcoinBaseEventsPayload {
  readonly fromTimestamp: number;
  readonly toTimestamp: number;
}

interface FromCacheGitcoinEventsPayload extends GitcoinBaseEventsPayload {
  readonly onlyCache: true;
}

export interface GitcoinGrantPayload extends GitcoinBaseEventsPayload {
  readonly grantId: number;
}

export type GitcoinGrantEventsPayload =
  | GitcoinGrantPayload
  | FromCacheGitcoinEventsPayload;

export type GitcoinReportPayload = GitcoinBaseEventsPayload & {
  readonly grantId?: number;
};

interface GitcoinGrant {
  readonly name: string;
  readonly events: GitcoinGrantEvents[];
  readonly createdOn: string;
}

export interface GitcoinGrants {
  readonly [grantId: string]: GitcoinGrant;
}

export interface GitcoinGrantEvents {
  readonly timestamp: number;
  readonly asset: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
  readonly grandId: number;
  readonly txId: string;
  readonly txType: 'ethereum' | 'zksync';
  readonly clrRound: Nullable<number>;
}

interface GitcoinGrantEarnings {
  readonly amount: BigNumber;
  readonly value: BigNumber;
}

interface GitcoinGrantPerAssetDetails {
  readonly [asset: string]: GitcoinGrantEarnings;
}

interface GitcoinGrantDetails {
  readonly perAsset: GitcoinGrantPerAssetDetails;
  readonly total: BigNumber;
}

interface GitcoinPerGrantReport {
  [grantId: string]: GitcoinGrantDetails;
}

export interface GitcoinGrantReport {
  readonly profitCurrency: string;
  readonly reports: GitcoinPerGrantReport;
}

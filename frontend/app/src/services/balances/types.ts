import { Balance, BigNumber } from '@rotki/common';
import {
  SUPPORTED_EXCHANGES,
  SUPPORTED_TRADE_LOCATIONS,
  EXTERNAL_EXCHANGES
} from '@/data/defaults';
import { TradeLocation } from '@/services/history/types';

export type SupportedExchange = typeof SUPPORTED_EXCHANGES[number];
export type SupportedTradeLocation = typeof SUPPORTED_TRADE_LOCATIONS[number];
export type SupportedExternalExchanges = typeof EXTERNAL_EXCHANGES[number];

export enum BalanceType {
  ASSET = 'asset',
  LIABILITY = 'liability'
}

export interface ManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: BigNumber;
  readonly location: TradeLocation;
  readonly tags: string[];
  readonly balanceType: BalanceType;
}

export interface ManualBalanceWithValue extends ManualBalance {
  readonly usdValue: BigNumber;
}

export interface ManualBalances {
  readonly balances: ManualBalanceWithValue[];
  readonly liabilities: Balances[];
}

interface BlockchainTotals {
  readonly assets: Balances;
  readonly liabilities: Balances;
}

export interface BlockchainBalances {
  readonly perAccount: {
    ETH: BlockchainAssetBalances;
    BTC: BtcBalances;
    KSM: BlockchainAssetBalances;
    DOT: BlockchainAssetBalances;
    AVAX: BlockchainAssetBalances;
  };
  readonly totals: BlockchainTotals;
}

interface XpubBalance {
  readonly xpub: string;
  readonly derivationPath: string;
  readonly addresses: Balances;
}

export interface BtcBalances {
  readonly standalone: Balances;
  readonly xpubs: XpubBalance[];
}

export interface EthBalance {
  readonly assets: Balances;
  readonly liabilities: Balances;
}

export interface BlockchainAssetBalances {
  [account: string]: EthBalance;
}

export interface Balances {
  [account: string]: Balance;
}

export type OracleCacheMeta = {
  readonly fromAsset: string;
  readonly toAsset: string;
  readonly fromTimestamp: string;
  readonly toTimestamp: string;
};

export type DataSourceMeta = {
  readonly id: string;
  readonly name: string;
};

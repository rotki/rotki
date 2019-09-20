import { BigNumber } from 'bignumber.js';

export interface BlockchainBalances {
  readonly per_account: {
    ETH: ApiEthBalances;
    BTC: ApiBalances;
  };
  readonly totals: ApiBalances;
}

export interface ApiBalance {
  readonly amount: string;
  readonly usd_value: string;
}

export interface ApiBalances {
  [account: string]: ApiBalance;
}

export interface ApiEthBalance {
  [asset: string]: string;
  readonly ETH: string;
  readonly usd_value: string;
}

export interface ApiEthBalances {
  [account: string]: ApiEthBalance;
}

export interface EthBalance {
  readonly eth: BigNumber;
  readonly usdValue: BigNumber;
  readonly tokens: AccountTokens;
}

export interface EthBalances {
  [account: string]: EthBalance;
}

export interface Balance {
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export interface Balances {
  [account: string]: Balance;
}

export interface AccountBalance {
  readonly account: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export interface AccountTokens {
  [token: string]: BigNumber;
}

export interface AssetBalance {
  readonly asset: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export interface FiatBalance {
  readonly currency: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
}

export interface ApiAssetBalance {
  readonly amount: string;
  readonly usd_value: string;
}

export interface AssetBalances {
  [asset: string]: Balance;
}

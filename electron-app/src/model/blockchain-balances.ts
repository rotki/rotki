import { Balances } from '@/typing/types';

export interface BlockchainBalances {
  readonly per_account: {
    [asset: string]: Balances;
  };
  readonly totals: Balances;
}

export interface ApiEthBalance {
  readonly ETH: string;
  readonly usd_value: string;
}

export interface EthBalance {
  readonly eth: number;
  readonly usdValue: number;
}

export interface ApiEthBalances {
  [account: string]: ApiEthBalance;
}

export interface EthBalances {
  [account: string]: EthBalance;
}

export interface ApiBalance {
  readonly amount: string;
  readonly usd_value: string;
}

export interface ApiBalances {
  [account: string]: ApiBalance;
}

export interface AccountBalance {
  readonly account: string;
  readonly amount: number;
  readonly usdValue: number;
}

import { Balances } from '@/typing/types';

export interface BlockchainBalances {
  readonly per_account: {
    [asset: string]: Balances;
  };
  readonly totals: Balances;
}

export interface EthBalance {
  readonly ETH: string;
  readonly usd_value: string;
}

export interface EthBalances {
  [account: string]: EthBalance;
}

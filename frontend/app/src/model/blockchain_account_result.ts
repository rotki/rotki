import { ApiBalances, ApiEthBalances } from '@/model/blockchain-balances';

export interface BlockchainAccount {
  readonly per_account: {
    ETH: ApiEthBalances;
    BTC: ApiBalances;
  };
  readonly totals: ApiBalances;
}

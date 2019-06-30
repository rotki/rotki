import { ApiBalances, ApiEthBalances } from '@/model/blockchain-balances';

export interface BlockchainAccountResult {
  readonly result: boolean;
  readonly message: string;
  readonly per_account: {
    ETH: ApiEthBalances;
    BTC: ApiBalances;
  };
  readonly totals: ApiBalances;
}

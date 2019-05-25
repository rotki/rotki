import { Balances } from '@/typing/types';

export interface BlockchainBalances {
  readonly per_account: {
    [asset: string]: Balances;
  };
  readonly totals: Balances;
}

import { Balances } from '@/typing/types';

export interface BlockchainAccountResult {
  readonly result: boolean;
  readonly message: string;
  readonly per_account: {
    [asset: string]: Balances;
  };
  readonly totals: Balances;
}

import { ApiAssetBalances } from '@/typing/types';

export interface ExchangeBalanceResult {
  readonly name: string;
  readonly error?: string;
  readonly balances: ApiAssetBalances;
}

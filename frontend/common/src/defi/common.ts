import type { Balance } from '../balances';

export interface ProfitLossModel {
  readonly address: string;
  readonly asset: string;
  readonly value: Balance;
}

export enum LpType {
  UNISWAP_V2 = 'UNISWAP_V2',
  SUSHISWAP = 'SUSHISWAP',
}

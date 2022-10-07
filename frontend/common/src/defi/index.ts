import { Balance } from "../index";

export interface ProfitLossModel {
  readonly address: string;
  readonly asset: string;
  readonly value: Balance;
}

export enum LpType {
  UNISWAP_V2 = 'UNISWAP_V2',
  UNISWAP_V3 = 'UNISWAP_V3',
  SUSHISWAP = 'SUSHISWAP',
  BALANCER = 'BALANCER'
}


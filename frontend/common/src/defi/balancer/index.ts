import { default as BigNumber } from "bignumber.js";
import { Balance } from "../../index";


export interface BalancerUnderlyingToken {
  readonly token: string;
  readonly totalAmount: BigNumber;
  readonly userBalance: Balance;
  readonly usdPrice: BigNumber;
  readonly weight: string;
}

interface BalancerBalance {
  readonly address: string;
  readonly tokens: BalancerUnderlyingToken[];
  readonly totalAmount: BigNumber;
  readonly userBalance: Balance;
}

export interface BalancerBalanceWithOwner extends BalancerBalance {
  readonly owner: string;
}

export interface BalancerBalances {
  readonly [address: string]: BalancerBalance[];
}

interface PoolToken {
  readonly token: string;
  readonly weight: string;
}

export interface PoolAmounts {
  readonly [asset: string]: BigNumber;
}

export type Pool = {
  readonly name: string;
  readonly address: string;
};

export interface BalancerEvent {
  readonly txHash: string;
  readonly logIndex: number;
  readonly timestamp: number;
  readonly eventType: 'mint' | 'burn';
  readonly lpBalance: Balance;
  readonly amounts: PoolAmounts;
  readonly pool?: Pool;
}

interface BalancerPoolDetails {
  readonly poolAddress: string;
  readonly poolTokens: PoolToken[];
  readonly events: BalancerEvent[];
  readonly profitLossAmounts: PoolAmounts;
  readonly usdProfitLoss: BigNumber;
}

export interface BalancerEvents {
  readonly [address: string]: BalancerPoolDetails[];
}

export interface BalancerProfitLoss {
  readonly pool: Pool;
  readonly tokens: string[];
  readonly usdProfitLoss: BigNumber;
  readonly profitLossAmount: PoolAmounts;
}
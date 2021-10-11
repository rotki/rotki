import { default as BigNumber } from "bignumber.js";
import { Balance } from "../../index";


export interface AdexBalance {
  readonly contractAddress: string;
  readonly adxBalance: Balance;
  readonly daiUnclaimedBalance: Balance;
  readonly poolId: string;
  readonly poolName: string;
}

export interface AdexBalances {
  readonly [address: string]: AdexBalance[];
}

export interface AdexEvent {
  readonly value: BigNumber;
  readonly eventType: "claim" | "deposit" | "withdraw";
  readonly bondId: string;
  readonly identityAddress: string;
  readonly poolId: string;
  readonly poolName: string;
  readonly timestamp: number;
  readonly txHash: string;
  readonly token: string | null;
}

export interface AdexStakingDetails {
  readonly contractAddress: string;
  readonly apr: string;
  readonly adxBalance: Balance;
  readonly daiUnclaimedBalance: Balance;
  readonly adxUnclaimedBalance: Balance;
  readonly adxProfitLoss: Balance;
  readonly daiProfitLoss: Balance;
  readonly poolId: string;
  readonly poolName: string;
  readonly totalStakedAmount: BigNumber;
}

export interface AdexDetails {
  readonly events: AdexEvent[];
  readonly stakingDetails: AdexStakingDetails[];
}

export interface AdexHistory {
  readonly [address: string]: AdexDetails;
}
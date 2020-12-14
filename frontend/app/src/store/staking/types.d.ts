import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/services/types-api';

export interface StakingState {
  readonly eth2Details: Eth2Detail[];
  readonly eth2Deposits: Eth2Deposit[];
  readonly adexBalances: AdexBalances;
  readonly adexEvents: AdexEvents;
}

export interface Eth2Deposit {
  readonly fromAddress: string;
  readonly pubkey: string;
  readonly withdrawalCredentials: string;
  readonly value: Balance;
  readonly depositIndex: number;
  readonly txHash: string;
  readonly logIndex: number;
}

interface Eth2Detail {
  readonly eth1Depositor: string;
  readonly index: number;
  readonly balance: Balance;
  readonly performance1d: Balance;
  readonly performance1w: Balance;
  readonly performance1m: Balance;
  readonly performance1y: Balance;
}

export interface Eth2Staking {
  readonly deposits: Eth2Deposit[];
  readonly details: Eth2Detail[];
}

interface AdexBalance {
  readonly address: string;
  readonly balance: Balance;
  readonly poolId: string;
  readonly poolName: string;
}

export interface AdexBalances {
  readonly [address: string]: AdexBalance[];
}

interface AdexEvent {
  readonly amount: BigNumber;
  readonly bondId: string;
  readonly identityAddress: string;
  readonly timestamp: number;
  readonly txHash: string;
}

interface AdexStat {
  readonly address: string;
  readonly apr: string;
  readonly balance: Balance;
  readonly poolId: string;
  readonly poolName: string;
  readonly totalStakedAmount: BigNumber;
}

interface AdexDetails {
  readonly events: AdexEvent[];
  readonly stakingStats: AdexStat[];
}

export interface AdexEvents {
  readonly [address: string]: AdexDetails;
}

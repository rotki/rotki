import { default as BigNumber } from 'bignumber.js';
import { Balance } from '@/services/types-api';

export interface StakingState {
  readonly eth2Details: Eth2Detail[];
  readonly eth2Deposits: Eth2Deposit[];
  readonly adexBalances: AdexBalances;
  readonly adexHistory: AdexHistory;
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

interface Eth2DailyStat {
  readonly timestamp: number;
  readonly pnl: Balance;
  readonly startBalance: Balance;
  readonly endBalance: Balance;
  readonly missedAttestations: number;
  readonly orphanedAttestations: number;
  readonly proposedBlocks: number;
  readonly missedBlocks: number;
  readonly orphanedBlocks: number;
  readonly includedAttesterSlashings: number;
  readonly proposerAttesterSlashings: number;
  readonly depositsNumber: number;
  readonly depositedBalance: Balance;
}

interface Eth2Detail {
  readonly eth1Depositor: string;
  readonly index: number;
  readonly balance: Balance;
  readonly performance1d: Balance;
  readonly performance1w: Balance;
  readonly performance1m: Balance;
  readonly performance1y: Balance;
  readonly dailyStats: Eth2DailyStat[];
}

interface AdexBalance {
  readonly contractAddress: string;
  readonly adxBalance: Balance;
  readonly daiUnclaimedBalance: Balance;
  readonly poolId: string;
  readonly poolName: string;
}

export interface AdexBalances {
  readonly [address: string]: AdexBalance[];
}

interface AdexEvent {
  readonly value: BigNumber;
  readonly eventType: 'claim' | 'deposit' | 'withdraw';
  readonly bondId: string;
  readonly identityAddress: string;
  readonly poolId: string;
  readonly poolName: string;
  readonly timestamp: number;
  readonly txHash: string;
  readonly token: string | null;
}

interface AdexStakingDetails {
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

interface AdexDetails {
  readonly events: AdexEvent[];
  readonly stakingDetails: AdexStakingDetails[];
}

export interface AdexHistory {
  readonly [address: string]: AdexDetails;
}

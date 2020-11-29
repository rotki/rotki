import { Balance } from '@/services/types-api';

export interface StakingState {
  eth2: Eth2Staking;
}

export interface Eth2Deposit {
  readonly fromAddress: string;
  readonly pubkey: string;
  readonly withdrawalCredentials: string;
  readonly value: Balance;
  readonly validatorIndex: number;
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

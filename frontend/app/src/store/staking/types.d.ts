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

interface Eth2Total {
  readonly [address: string]: Balance;
}

export interface Eth2Staking {
  readonly deposits: Eth2Deposit[];
  readonly totals: Eth2Total;
}

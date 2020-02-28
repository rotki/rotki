import { DSRMovementType } from '@/services/types-common';

export interface ApiDSRBalances {
  readonly current_dsr: string;
  readonly balances: { [account: string]: string };
}

export interface ApiDSRMovement {
  readonly movement_type: DSRMovementType;
  readonly gain_so_far: string;
  readonly amount: string;
  readonly block_number: number;
  readonly timestamp: number;
}

export interface ApiDSRHistory {
  readonly [address: string]: ApiDSRMovement;
}

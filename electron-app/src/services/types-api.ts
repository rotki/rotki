import { DSRMovementType } from '@/services/types-common';

export interface ApiDSRBalances {
  [account: string]: string;
}

export interface ApiDSRMovement {
  readonly movement_type: DSRMovementType;
  readonly gain_so_far: string;
  readonly amount: string;
  readonly block_number: number;
}

export interface ApiDSRHistory {
  [address: string]: ApiDSRMovement;
}

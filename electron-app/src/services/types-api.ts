import {
  DSRMovementType,
  SupportedAsset,
  Location
} from '@/services/types-common';

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
  readonly [address: string]: {
    gain_so_far: string;
    movements: ApiDSRMovement[];
  };
}

export interface SupportedAssets {
  readonly [asset: string]: SupportedAsset;
}

export interface ApiManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: string;
  readonly location: Location;
  readonly tags: string[];
}

export interface ApiManualBalanceWithValue extends ApiManualBalance {
  readonly usd_value: string;
}

export interface ApiManualBalances {
  readonly balances: ApiManualBalanceWithValue[];
}

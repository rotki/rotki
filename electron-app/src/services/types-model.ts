import { default as BigNumber } from 'bignumber.js';
import { DSRMovementType, Location } from '@/services/types-common';

export interface DSRBalances {
  readonly currentDSR: BigNumber;
  readonly balances: { [account: string]: BigNumber };
}

export interface DSRHistory {
  readonly [address: string]: {
    gainSoFar: BigNumber;
    movements: DSRMovement[];
  };
}

export interface DSRMovement {
  readonly movementType: DSRMovementType;
  readonly gainSoFar: BigNumber;
  readonly amount: BigNumber;
  readonly blockNumber: number;
  readonly timestamp: number;
}

export interface ManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: BigNumber;
  readonly usdValue: BigNumber;
  readonly location: Location;
  readonly tags: string[];
}

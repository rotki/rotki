import { default as BigNumber } from 'bignumber.js';
import { DSRMovementType } from '@/services/types-common';

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

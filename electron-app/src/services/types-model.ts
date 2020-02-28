import BigNumber from 'bignumber.js';
import { DSRMovementType } from '@/services/types-common';

export interface DSRBalances {
  [account: string]: BigNumber;
}

export interface DSRHistory {
  [address: string]: DSRMovement;
}

export interface DSRMovement {
  readonly movementType: DSRMovementType;
  readonly gainSoFar: BigNumber;
  readonly amount: BigNumber;
  readonly blockNumber: number;
}

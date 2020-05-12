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

export interface SupportedAsset {
  readonly key: string;
  readonly active?: boolean;
  readonly ended?: number;
  readonly name: string;
  readonly started?: number;
  readonly symbol: string;
  readonly type: string;
}

export interface MakerDAOVault {
  readonly identifier: number;
  readonly name: string;
  readonly collateralAsset: string;
  readonly collateralAmount: BigNumber;
  readonly debtValue: BigNumber;
  readonly liquidationRatio: string;
  readonly collateralizationRatio?: string;
}

import { default as BigNumber } from 'bignumber.js';
import {
  CollateralAssetType,
  DSRMovementType,
  Location,
  MakerDAOVaultEventType
} from '@/services/types-common';

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
  readonly collateralType: string;
  readonly collateralAsset: CollateralAssetType;
  readonly collateralAmount: BigNumber;
  readonly debtValue: BigNumber;
  readonly collateralizationRatio?: string;
  readonly liquidationRatio: string;
  readonly liquidationPrice: BigNumber;
  readonly collateralUsdValue: BigNumber;
}

export interface MakerDAOVaultDetails {
  readonly identifier: number;
  readonly creationTs: number;
  readonly totalInterestOwed: BigNumber;
  readonly totalLiquidatedAmount: BigNumber;
  readonly totalLiquidatedUsd: BigNumber;
  readonly events: MakerDAOVaultEvent[];
}

export interface MakerDAOVaultEvent {
  readonly eventType: MakerDAOVaultEventType;
  readonly amount: BigNumber;
  readonly amountUsdValue: BigNumber;
  readonly timestamp: number;
  readonly txHash: string;
}

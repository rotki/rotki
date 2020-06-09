import { default as BigNumber } from 'bignumber.js';
import {
  CollateralAssetType,
  DSRMovementType,
  Location,
  MakerDAOVaultEventType,
  WatcherType
} from '@/services/types-common';

export interface DSRBalances {
  readonly currentDSR: BigNumber;
  readonly balances: {
    [account: string]: {
      amount: BigNumber;
      usdValue: BigNumber;
    };
  };
}

export interface DSRHistoryItem {
  readonly gainSoFar: BigNumber;
  readonly gainSoFarUsdValue: BigNumber;
  readonly movements: DSRMovement[];
}

export interface DSRHistory {
  readonly [address: string]: DSRHistoryItem;
}

export interface DSRMovement {
  readonly movementType: DSRMovementType;
  readonly gainSoFar: BigNumber;
  readonly gainSoFarUsdValue: BigNumber;
  readonly amount: BigNumber;
  readonly amountUsdValue: BigNumber;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly txHash: string;
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

export interface Watcher {
  readonly identifier: string;
  readonly type: WatcherType;
  readonly args: object;
}

export interface MakerDAOVault {
  readonly identifier: number;
  readonly collateralType: string;
  readonly collateralAsset: CollateralAssetType;
  readonly collateralAmount: BigNumber;
  readonly debtValue: BigNumber;
  readonly collateralizationRatio?: string;
  readonly stabilityFee: string;
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

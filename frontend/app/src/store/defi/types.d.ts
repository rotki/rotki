import { default as BigNumber } from 'bignumber.js';
import { ApiBalance, Balance } from '@/model/blockchain-balances';
import {
  AaveEventType,
  CollateralAssetType,
  DSRMovementType,
  MakerDAOVaultEventType
} from '@/services/defi/types';

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

export type MakerDAOVaultModel =
  | MakerDAOVault
  | (MakerDAOVault & MakerDAOVaultDetails);

export interface MakerDAOVaultSummary {
  readonly totalCollateralUsd: BigNumber;
  readonly totalDebt: BigNumber;
}

export interface AaveAsset {
  readonly apy?: string;
  readonly stableApy?: string;
  readonly variableApy?: string;
  readonly balance: Balance;
}

export interface AaveBorrowing {
  readonly [asset: string]: AaveAsset;
}

export interface AaveLending {
  readonly [asset: string]: AaveAsset;
}

interface AaveBalance {
  readonly lending: AaveLending;
  readonly borrowing: AaveBorrowing;
}

export interface AaveBalances {
  readonly [address: string]: AaveBalance;
}

export interface AaveHistoryEvents {
  eventType: AaveEventType;
  asset: string;
  value: Balance;
  blockNumber: number;
  timestamp: number;
  txHash: string;
}

export interface AaveHistoryTotalEarned {
  readonly [asset: string]: Balance;
}

export interface AaveAccountHistory {
  readonly events: AaveHistoryEvents[];
  readonly totalEarned: AaveHistoryTotalEarned;
}

export interface AaveHistory {
  readonly [address: string]: AaveAccountHistory;
}

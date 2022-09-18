import { Balance, BigNumber } from '@rotki/common';
import { balanceKeys } from '@/services/consts';
import {
  Collateral,
  CollateralAssetType,
  CollateralizedLoan
} from '@/types/defi/index';

export type DSRMovementType = 'withdrawal' | 'deposit';
export type MakerDAOVaultEventType =
  | 'deposit'
  | 'withdraw'
  | 'generate'
  | 'payback'
  | 'liquidation';

export interface ApiMakerDAOVault {
  readonly identifier: number;
  readonly collateralType: string;
  readonly owner: string;
  readonly collateralAsset: CollateralAssetType;
  readonly collateral: Balance;
  readonly debt: Balance;
  readonly collateralizationRatio: string | null;
  readonly liquidationRatio: string;
  readonly liquidationPrice: BigNumber | null;
  readonly stabilityFee: string;
}

export interface DSRBalances {
  readonly currentDsr: BigNumber;
  readonly balances: {
    [account: string]: {
      amount: BigNumber;
      usdValue: BigNumber;
    };
  };
}

interface DSRHistoryItem {
  readonly gainSoFar: Balance;
  readonly movements: DSRMovement[];
}

export interface DSRHistory {
  readonly [address: string]: DSRHistoryItem;
}

interface DSRMovement {
  readonly movementType: DSRMovementType;
  readonly gainSoFar: Balance;
  readonly value: Balance;
  readonly blockNumber: number;
  readonly timestamp: number;
  readonly txHash: string;
}

export interface MakerDAOVault
  extends CollateralizedLoan<Collateral<CollateralAssetType>> {
  readonly collateralType: string;
  readonly collateralizationRatio?: string;
  readonly stabilityFee: string;
  readonly liquidationRatio: string;
  readonly liquidationPrice: BigNumber;
}

export interface MakerDAOVaultDetails {
  readonly identifier: string;
  readonly creationTs: number;
  readonly totalInterestOwed: BigNumber;
  readonly totalLiquidated: Balance;
  readonly events: MakerDAOVaultEvent[];
}

export interface MakerDAOVaultEvent {
  readonly eventType: MakerDAOVaultEventType;
  readonly value: Balance;
  readonly timestamp: number;
  readonly txHash: string;
}

export type MakerDAOVaultModel =
  | MakerDAOVault
  | (MakerDAOVault & MakerDAOVaultDetails);

export interface MakerDAOLendingHistoryExtras {
  gainSoFar: Balance;
}

export const dsrKeys = [...balanceKeys, 'current_dsr'];
export const vaultDetailsKeys = [...balanceKeys, 'total_interest_owed'];
export const vaultKeys = [...balanceKeys, 'liquidation_price'];

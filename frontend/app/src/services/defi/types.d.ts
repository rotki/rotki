import { Balance, BigNumber } from '@rotki/common';
import { AaveEventType } from '@rotki/common/lib/defi/aave';
import { CompoundEventType } from '@/services/defi/types/compound';

export type DSRMovementType = 'withdrawal' | 'deposit';
export type MakerDAOVaultEventType =
  | 'deposit'
  | 'withdraw'
  | 'generate'
  | 'payback'
  | 'liquidation';

export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';
export type DefiBalanceType = 'Asset' | 'Debt';

export type EventType = DSRMovementType | AaveEventType | CompoundEventType;

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

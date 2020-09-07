import { default as BigNumber } from 'bignumber.js';
import { DEFI_PROTOCOLS } from '@/services/defi/consts';
import { Balance } from '@/services/types-api';

export type DSRMovementType = 'withdrawal' | 'deposit';
export type MakerDAOVaultEventType =
  | 'deposit'
  | 'withdraw'
  | 'generate'
  | 'payback'
  | 'liquidation';
export type AaveEventType = 'deposit' | 'interest' | 'withdrawal';
export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';
export type DefiBalanceType = 'Asset' | 'Debt';

export type SupportedDefiProtocols = typeof DEFI_PROTOCOLS[number];

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

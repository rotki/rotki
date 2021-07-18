import { default as BigNumber } from 'bignumber.js';
import {
  AAVE_BORROWING_EVENTS,
  AAVE_LENDING_EVENTS,
  DEFI_PROTOCOLS,
  PROTOCOL_VERSION
} from '@/services/defi/consts';
import { CompoundEventType } from '@/services/defi/types/compound';
import { Balance } from '@/services/types-api';

export type DSRMovementType = 'withdrawal' | 'deposit';
export type MakerDAOVaultEventType =
  | 'deposit'
  | 'withdraw'
  | 'generate'
  | 'payback'
  | 'liquidation';

export type AaveBorrowingEventType = typeof AAVE_BORROWING_EVENTS[number];
type AaveLendingEventType = typeof AAVE_LENDING_EVENTS[number];

export type AaveEventType = AaveLendingEventType | AaveBorrowingEventType;

export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';
export type DefiBalanceType = 'Asset' | 'Debt';

export type SupportedDefiProtocols = typeof DEFI_PROTOCOLS[number];

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

export type ProtocolVersion = typeof PROTOCOL_VERSION[number];

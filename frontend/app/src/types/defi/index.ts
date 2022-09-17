import { Balance } from '@rotki/common';
import { DefiProtocol } from '@rotki/common/lib/blockchain';

export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';
export type DefiBalanceType = 'Asset' | 'Debt';

export interface Collateral<T extends CollateralAssetType | string>
  extends Balance {
  readonly asset: T;
}

export interface CollateralizedLoan<
  C extends
    | Collateral<CollateralAssetType | string>
    | Collateral<CollateralAssetType | string>[]
> extends DefiLoan {
  readonly collateral: C;
  readonly debt: Balance;
}

export interface DefiLoan {
  readonly identifier: string;
  readonly protocol: DefiProtocol;
  readonly asset?: string;
  readonly owner?: string;
}

export interface AssetMovement {
  readonly asset: string;
  readonly value: Balance;
  readonly toAsset: string;
  readonly toValue: Balance;
}

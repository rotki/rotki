import { type Balance } from '@rotki/common';
import { type DefiProtocol } from '@rotki/common/lib/blockchain';

export interface Collateral<T = string> extends Balance {
  readonly asset: T;
}

export interface CollateralizedLoan<C extends Collateral | Collateral[]>
  extends DefiLoan {
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

export enum ProtocolVersion {
  V1 = 'v1',
  V2 = 'v2'
}

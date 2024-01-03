import { type Balance } from '@rotki/common';
import { type Blockchain } from '@rotki/common/lib/blockchain';
import { type Account } from '@rotki/common/lib/account';
import { type DefiProtocol } from '@/types/modules';

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
  readonly label?: string;
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

export interface ProtocolMetadata {
  identifier: string;
  name: string;
  icon: string;
}

export interface DefiAccount<T = Blockchain> extends Account<T> {
  readonly protocols: DefiProtocol[];
}

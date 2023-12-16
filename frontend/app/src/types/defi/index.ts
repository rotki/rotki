import type { AddressData, BlockchainAccount } from '@/types/blockchain/accounts';
import type { Balance } from '@rotki/common';
import type { DefiProtocol } from '@/types/modules';

export interface Collateral<T = string> extends Balance {
  readonly asset: T;
}

export interface CollateralizedLoan<C extends Collateral | Collateral[]> extends DefiLoan {
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

export enum ProtocolVersion {
  V1 = 'v1',
  V2 = 'v2',
}

export interface ProtocolMetadata {
  identifier: string;
  name: string;
  icon: string;
  iconUrl?: string;
}

export interface DefiAccount extends BlockchainAccount<AddressData> {
  readonly protocols: DefiProtocol[];
}

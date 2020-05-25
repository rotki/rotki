import {
  CollateralAssetType,
  DSRMovementType,
  Location,
  MakerDAOVaultEventType
} from '@/services/types-common';

export interface ApiDSRBalances {
  readonly current_dsr: string;
  readonly balances: { [account: string]: string };
}

export interface ApiDSRMovement {
  readonly movement_type: DSRMovementType;
  readonly gain_so_far: string;
  readonly amount: string;
  readonly block_number: number;
  readonly timestamp: number;
}

export interface ApiDSRHistory {
  readonly [address: string]: {
    gain_so_far: string;
    movements: ApiDSRMovement[];
  };
}

export interface ApiSupportedAsset {
  readonly active?: boolean;
  readonly ended?: number;
  readonly name: string;
  readonly started?: number;
  readonly symbol: string;
  readonly type: string;
}

export interface SupportedAssets {
  readonly [key: string]: ApiSupportedAsset;
}

export interface ApiManualBalance {
  readonly asset: string;
  readonly label: string;
  readonly amount: string;
  readonly location: Location;
  readonly tags: string[];
}

export interface ApiManualBalanceWithValue extends ApiManualBalance {
  readonly usd_value: string;
}

export interface ApiManualBalances {
  readonly balances: ApiManualBalanceWithValue[];
}

export interface ApiMakerDAOVault {
  readonly identifier: number;
  readonly collateral_type: string;
  readonly owner: string;
  readonly collateral_asset: CollateralAssetType;
  readonly collateral_amount: string;
  readonly debt_value: string;
  readonly collateralization_ratio: string | null;
  readonly liquidation_ratio: string;
  readonly liquidation_price: string;
  readonly collateral_usd_value: string;
  readonly stability_fee: string;
}

export interface ApiMakerDAOVaultDetails {
  readonly identifier: number;
  readonly creation_ts: number;
  readonly total_interest_owed: string;
  readonly total_liquidated_amount: string;
  readonly total_liquidated_usd: string;
  readonly events: ApiMakerDAOVaultEvent[];
}

export interface ApiMakerDAOVaultEvent {
  readonly event_type: MakerDAOVaultEventType;
  readonly amount: string;
  readonly timestamp: number;
  readonly tx_hash: string;
}

export class TaskNotFoundError extends Error {}

export interface ApiDSRBalances {
  readonly current_dsr: string;
  readonly balances: {
    readonly [account: string]: {
      amount: string;
      usd_value: string;
    };
  };
}

export type DSRMovementType = 'withdrawal' | 'deposit';
export type MakerDAOVaultEventType =
  | 'deposit'
  | 'withdraw'
  | 'generate'
  | 'payback'
  | 'liquidation';
export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';

export interface ApiDSRMovement {
  readonly movement_type: DSRMovementType;
  readonly gain_so_far: string;
  readonly gain_so_far_usd_value: string;
  readonly amount: string;
  readonly amount_usd_value: string;
  readonly block_number: number;
  readonly timestamp: number;
  readonly tx_hash: string;
}

export interface ApiDSRHistory {
  readonly [address: string]: {
    gain_so_far: string;
    gain_so_far_usd_value: string;
    movements: ApiDSRMovement[];
  };
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
  readonly amount_usd_value: string;
  readonly timestamp: number;
  readonly tx_hash: string;
}

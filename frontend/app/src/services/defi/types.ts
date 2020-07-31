import { ApiBalance } from '@/model/blockchain-balances';

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
export type AaveEventType = 'deposit' | 'interest' | 'withdrawal';
export type CollateralAssetType = 'ETH' | 'BAT' | 'USDC' | 'WBTC';
export type DefiBalanceType = 'Asset' | 'Debt';

export const DEFI_PROTOCOLS = ['aave', 'makerdao'] as const;
export type SupportedDefiProtocols = typeof DEFI_PROTOCOLS[number];

export interface ApiDSRMovement {
  readonly movement_type: DSRMovementType;
  readonly gain_so_far: {
    amount: string;
    usd_value: string;
  };
  readonly value: {
    amount: string;
    usd_value: string;
  };
  readonly block_number: number;
  readonly timestamp: number;
  readonly tx_hash: string;
}

export interface ApiDSRHistory {
  readonly [address: string]: {
    gain_so_far: {
      amount: string;
      usd_value: string;
    };
    movements: ApiDSRMovement[];
  };
}

export interface ApiMakerDAOVault {
  readonly identifier: number;
  readonly collateral_type: string;
  readonly owner: string;
  readonly collateral_asset: CollateralAssetType;
  readonly collateral: {
    amount: string;
    usd_value: string;
  };
  readonly debt: {
    amount: string;
    usd_value: string;
  };
  readonly collateralization_ratio: string | null;
  readonly liquidation_ratio: string;
  readonly liquidation_price: string;
  readonly stability_fee: string;
}

export interface ApiMakerDAOVaultDetails {
  readonly identifier: number;
  readonly creation_ts: number;
  readonly total_interest_owed: string;
  readonly total_liquidated: {
    amount: string;
    usd_value: string;
  };
  readonly events: ApiMakerDAOVaultEvent[];
}

export interface ApiMakerDAOVaultEvent {
  readonly event_type: MakerDAOVaultEventType;
  readonly value: {
    amount: string;
    usd_value: string;
  };
  readonly timestamp: number;
  readonly tx_hash: string;
}

export interface ApiAaveAsset {
  readonly balance: ApiBalance;
}

export interface ApiAaveBorrowingAsset extends ApiAaveAsset {
  readonly stable_apr: string;
  readonly variable_apr: string;
}

export interface ApiAaveLendingAsset extends ApiAaveAsset {
  readonly apy: string;
}

export interface ApiAaveBorrowing {
  readonly [asset: string]: ApiAaveBorrowingAsset;
}

export interface ApiAaveLending {
  readonly [asset: string]: ApiAaveLendingAsset;
}

interface ApiAaveBalance {
  readonly lending: ApiAaveLending;
  readonly borrowing: ApiAaveBorrowing;
}

export interface ApiAaveBalances {
  readonly [address: string]: ApiAaveBalance;
}

export interface ApiAaveHistoryEvents {
  event_type: AaveEventType;
  asset: string;
  value: ApiBalance;
  block_number: number;
  timestamp: number;
  tx_hash: string;
}

export interface ApiAaveHistoryTotalEarned {
  readonly [asset: string]: ApiBalance;
}

export interface ApiAaveAccountHistory {
  readonly events: ApiAaveHistoryEvents[];
  readonly total_earned: ApiAaveHistoryTotalEarned;
}

export interface ApiAaveHistory {
  readonly [address: string]: ApiAaveAccountHistory;
}

export interface ApiDefiProtocolInfo {
  readonly name: string;
  readonly icon: string;
}

export interface ApiDefiAsset {
  readonly token_address: string;
  readonly token_name: string;
  readonly token_symbol: string;
  readonly balance: ApiBalance;
}

export interface ApiDefiProtocolData {
  readonly protocol: ApiDefiProtocolInfo;
  readonly balance_type: DefiBalanceType;
  readonly base_balance: ApiDefiAsset;
  readonly underlying_balances: ApiDefiAsset[];
}

export interface ApiAllDefiProtocols {
  readonly [asset: string]: ApiDefiProtocolData[];
}

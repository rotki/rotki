import { SupportedExchange } from '@/services/balances/types';
import { SupportedModules } from '@/services/session/types';
import { KrakenAccountType } from '@/store/balances/types';
import { LedgerActionType } from '@/store/history/consts';

const PRICE_ORACLES = ['cryptocompare', 'coingecko'] as const;
export type PriceOracles = typeof PRICE_ORACLES[number];

export interface Exchange {
  readonly location: SupportedExchange;
  readonly name: string;
  readonly krakenAccountType?: KrakenAccountType;
  readonly ftxSubaccount?: string;
}

export interface AccountState {
  readonly premium: boolean;
  readonly settings: DBSettings;
  readonly exchanges: Exchange[];
}

export interface DBSettings {
  readonly taxable_ledger_actions: LedgerActionType[];
  readonly have_premium: boolean;
  readonly version: number;
  readonly last_write_ts: number;
  readonly premium_should_sync?: boolean;
  readonly submit_usage_analytics: boolean;
  readonly include_crypto2crypto: boolean;
  readonly include_gas_costs: boolean;
  readonly last_data_upload_ts: number;
  readonly ui_floating_precision: number;
  readonly taxfree_after_period: number;
  readonly balance_save_frequency: number;
  readonly eth_rpc_endpoint: string;
  readonly ksm_rpc_endpoint: string;
  readonly main_currency: string;
  readonly last_balance_save: number;
  readonly date_display_format: string;
  readonly kraken_account_type: string;
  readonly active_modules: SupportedModules[];
  readonly frontend_settings: string;
  readonly account_for_assets_movements: boolean;
  readonly btc_derivation_gap_limit: number;
  readonly calculate_past_cost_basis: boolean;
  readonly display_date_in_localtime: boolean;
  readonly current_price_oracles: PriceOracles[];
  readonly historical_price_oracles: PriceOracles[];
}

interface ApiKey {
  api_key: string;
}

export interface ExternalServiceKeys {
  etherscan?: ApiKey;
  cryptocompare?: ApiKey;
  beaconchain?: ApiKey;
  loopring?: ApiKey;
}

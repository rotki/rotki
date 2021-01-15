import { SupportedModules } from '@/services/session/types';
import { GeneralSettings } from '@/typing/types';

export interface AccountState {
  readonly premium: boolean;
  readonly settings: DBSettings;
  readonly exchanges: string[];
}

export interface DBSettings {
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
  readonly anonymized_logs: boolean;
  readonly date_display_format: string;
  readonly thousand_separator: string;
  readonly decimal_separator: string;
  readonly currency_location: GeneralSettings['currencyLocation'];
  readonly kraken_account_type: string;
  readonly active_modules: SupportedModules[];
  readonly frontend_settings: string;
  readonly account_for_assets_movements: boolean;
  readonly btc_derivation_gap_limit: number;
  readonly calculate_past_cost_basis: boolean;
}

interface ApiKey {
  api_key: string;
}

export interface ExternalServiceKeys {
  etherscan?: ApiKey;
  cryptocompare?: ApiKey;
  beaconchain?: ApiKey;
}

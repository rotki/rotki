export interface ActionResult<T> {
  readonly result: T;
  readonly message: string;
}

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
  readonly historical_data_start: string;
  readonly eth_rpc_endpoint: string;
  readonly main_currency: string;
  readonly last_balance_save: number;
  readonly anonymized_logs: boolean;
  readonly date_display_format: string;
  readonly kraken_account_type: string;
}

export interface AsyncQuery {
  readonly task_id: number;
}

export interface ApiKey {
  api_key: string;
}

export interface ExternalServiceKeys {
  etherscan?: ApiKey;
  cryptocompare?: ApiKey;
  alethio?: ApiKey;
}

export interface ApiAccountData {
  readonly address: string;
  readonly label: string | null;
  readonly tags: string[] | null;
}

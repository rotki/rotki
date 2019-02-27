export interface ActionResult<T> {
    readonly result: T;
    readonly message: string;
    readonly error?: string;
}

export interface UnlockResult extends ActionResult<boolean> {
    readonly permission_needed?: boolean;
    readonly premium: boolean;
    readonly settings?: DBSettings;
    readonly exchanges?: string[];
}

export interface DBSettings {
    readonly db_version: number;
    readonly last_write_ts: number;
    readonly premium_should_sync?: boolean;
    readonly include_crypto2crypto: boolean;
    readonly include_gas_costs: boolean;
    readonly last_data_upload_ts: number;
    readonly ui_floating_precision: number;
    readonly taxfree_after_period: number;
    readonly balance_save_frequency: number;
    readonly historical_data_start: string;
    readonly eth_rpc_port: string;
    readonly main_currency: string;
    readonly last_balance_save: number;
    readonly anonymized_logs: boolean;
    readonly date_display_format: string;
}

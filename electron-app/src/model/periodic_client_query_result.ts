export interface PeriodicClientQueryResult {
    readonly last_balance_save: number;
    readonly eth_node_connection: boolean;
    readonly history_process_start_ts: number;
    readonly history_process_current_ts: number;
}

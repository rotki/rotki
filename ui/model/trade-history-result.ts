import { EventEntry } from './event-entry';

export interface TradeHistoryResult {
    readonly overview: TradeHistoryOverview;
    readonly all_events: EventEntry[];
    readonly error?: string;
}

export interface TradeHistoryOverview {
    readonly [key: string]: number;

    readonly loan_profit: number;
    readonly margin_positions_profit: number;
    readonly settlement_losses: number;
    readonly ethereum_transaction_gas_costs: number;
    readonly asset_movement_fees: number;
    readonly general_trade_profit_loss: number;
    readonly taxable_trade_profit_loss: number;
    readonly total_taxable_profit_loss: number;
    readonly total_profit_loss: number;
}

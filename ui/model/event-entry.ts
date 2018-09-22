export interface EventEntry {
    readonly type: string;
    readonly paid_in_profit_currency: number;
    readonly paid_asset: string;
    readonly paid_in_asset: number;
    readonly taxable_amount: number;
    readonly taxable_bought_cost: number;
    readonly received_asset: string;
    readonly received_in_profit_currency: number;
    readonly received_in_asset: number;
    readonly net_profit_or_loss: number;
    readonly time: number;
    readonly is_virtual: boolean;
}
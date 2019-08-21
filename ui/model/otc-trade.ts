export interface OtcTrade {
    readonly id: number;
    readonly timestamp: number;
    readonly pair: string;
    readonly trade_type: string;
    readonly amount: string;
    readonly rate: string;
    readonly fee: string;
    readonly fee_currency: string;
    readonly link: string;
    readonly notes: string;
}

export interface StoredTrade extends Trade {
  readonly trade_id: string;
}

export interface TradePayload extends Trade {
  readonly trade_id?: string;
}

export interface Trade {
  readonly timestamp: number;
  readonly location: string;
  readonly pair: string;
  readonly trade_type: 'buy' | 'sell';
  readonly amount: string;
  readonly rate: string;
  readonly fee: string;
  readonly fee_currency: string;
  readonly link: string;
  readonly notes: string;
}

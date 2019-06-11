export interface OtcTrade {
  readonly id: number;
  readonly timestamp: number;
  readonly pair: string;
  readonly trade_type: 'buy' | 'sell';
  readonly amount: string;
  readonly rate: string;
  readonly fee: string;
  readonly fee_currency: string;
  readonly link: string;
  readonly notes: string;
}

export interface OtcPayload {
  readonly otc_id: number | null;
  readonly otc_timestamp: string;
  readonly otc_pair: string;
  readonly otc_type: 'buy' | 'sell';
  readonly otc_amount: string;
  readonly otc_rate: string;
  readonly otc_fee: string;
  readonly otc_fee_currency: string;
  readonly otc_link: string;
  readonly otc_notes: string;
}

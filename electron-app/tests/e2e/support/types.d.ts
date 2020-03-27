export type OTCTrade = {
  readonly time: string;
  readonly pair: string;
  readonly trade_type: 'buy' | 'sell';
  readonly amount: string;
  readonly rate: string;
  readonly fee: string;
  readonly fee_currency: string;
  readonly link: string;
  readonly notes: string;
};

export type TradeLocation =
  | 'kraken'
  | 'poloniex'
  | 'bitmex'
  | 'binance'
  | 'bittrex'
  | 'gemini'
  | 'coinbase'
  | 'coinbasepro'
  | 'ethereum'
  | 'bitcoin'
  | 'external';

export type TradeLocationData = {
  readonly identifier: TradeLocation;
  readonly name: string;
  readonly icon?: string;
};

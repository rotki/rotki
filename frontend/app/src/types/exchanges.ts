export const KRAKEN_ACCOUNT_TYPES = ['starter', 'intermediate', 'pro'] as const;
export type KrakenAccountType = typeof KRAKEN_ACCOUNT_TYPES[number];

export const EXCHANGE_POLONIEX = 'poloniex';
export const EXCHANGE_KRAKEN = 'kraken';
export const EXCHANGE_BITTREX = 'bittrex';
export const EXCHANGE_BITMEX = 'bitmex';
export const EXCHANGE_BITPANDA = 'bitpanda';
export const EXCHANGE_BITFINEX = 'bitfinex';
export const EXCHANGE_BINANCE = 'binance';
export const EXCHANGE_COINBASE = 'coinbase';
export const EXCHANGE_COINBASEPRO = 'coinbasepro';
export const EXCHANGE_BITSTAMP = 'bitstamp';
export const EXCHANGE_BINANCEUS = 'binanceus';
export const EXCHANGE_BITCOIN_DE = 'bitcoinde';
export const EXCHANGE_ICONOMI = 'iconomi';
export const EXCHANGE_KUCOIN = 'kucoin';
export const EXCHANGE_FTX = 'ftx';
export const EXCHANGE_INDEPENDENTRESERVE = 'independentreserve';
export const EXCHANGE_GEMINI = 'gemini';
/**
 * A list of exchanges that are supported via api connection
 */
export const SUPPORTED_EXCHANGES = [
  EXCHANGE_KRAKEN,
  EXCHANGE_POLONIEX,
  EXCHANGE_BITTREX,
  EXCHANGE_BITMEX,
  EXCHANGE_BITPANDA,
  EXCHANGE_BITFINEX,
  EXCHANGE_BINANCE,
  EXCHANGE_BINANCEUS,
  EXCHANGE_BITCOIN_DE,
  EXCHANGE_COINBASE,
  EXCHANGE_COINBASEPRO,
  EXCHANGE_GEMINI,
  EXCHANGE_ICONOMI,
  EXCHANGE_BITSTAMP,
  EXCHANGE_KUCOIN,
  EXCHANGE_FTX,
  EXCHANGE_INDEPENDENTRESERVE
] as const;
export type SupportedExchange = typeof SUPPORTED_EXCHANGES[number];

export interface Exchange {
  readonly location: SupportedExchange;
  readonly name: string;
  readonly krakenAccountType?: KrakenAccountType;
  readonly ftxSubaccount?: string;
}

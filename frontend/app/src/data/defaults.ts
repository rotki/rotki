import { CURRENCY_AFTER, CurrencyLocation } from '@/typing/types';

export class Defaults {
  static DEFAULT_DATE_DISPLAY_FORMAT = '%d/%m/%Y %H:%M:%S %Z';
  static DEFAULT_THOUSAND_SEPARATOR = ',';
  static DEFAULT_DECIMAL_SEPARATOR = '.';
  static DEFAULT_CURRENCY_LOCATION: CurrencyLocation = CURRENCY_AFTER;
  static FLOATING_PRECISION = 2;
  static RPC_ENDPOINT = 'http://localhost:8545';
  static KSM_RPC_ENDPOINT = 'http://localhost:9933';
  static BALANCE_SAVE_FREQUENCY = 24;
  static ANONYMIZED_LOGS = false;
  static ANONYMOUS_USAGE_ANALYTICS = true;
  static KRAKEN_DEFAULT_ACCOUNT_TYPE = 'starter';
  static DEFAULT_QUERY_PERIOD = 5;
  static BTC_DERIVATION_GAP_LIMIT = 20;
}

export const EXCHANGE_POLONIEX = 'poloniex';
export const EXCHANGE_KRAKEN = 'kraken';
export const EXCHANGE_BITTREX = 'bittrex';
export const EXCHANGE_BITMEX = 'bitmex';
export const EXCHANGE_BITFINEX = 'bitfinex';
export const EXCHANGE_BINANCE = 'binance';
export const EXCHANGE_COINBASE = 'coinbase';
export const EXCHANGE_COINBASEPRO = 'coinbasepro';
export const EXCHANGE_GEMINI = 'gemini';
export const EXCHANGE_CRYPTOCOM = 'crypto.com';
export const EXCHANGE_BITSTAMP = 'bitstamp';
export const EXCHANGE_BINANCE_US = 'binance_us';
export const EXCHANGE_BITCOIN_DE = 'bitcoinde';
export const EXCHANGE_ICONOMI = 'iconomi';

export const EXCHANGE_UNISWAP = 'uniswap';

export const TRADE_LOCATION_EXTERNAL = 'external';
export const TRADE_LOCATION_BANKS = 'banks';
export const TRADE_LOCATION_EQUITIES = 'equities';
export const TRADE_LOCATION_REALESTATE = 'realestate';
export const TRADE_LOCATION_COMMODITIES = 'commodities';
export const TRADE_LOCATION_BLOCKCHAIN = 'blockchain';

/**
 * A list of exchanges that are supported via api connection
 */
export const SUPPORTED_EXCHANGES = [
  EXCHANGE_KRAKEN,
  EXCHANGE_POLONIEX,
  EXCHANGE_BITTREX,
  EXCHANGE_BITMEX,
  EXCHANGE_BITFINEX,
  EXCHANGE_BINANCE,
  EXCHANGE_BINANCE_US,
  EXCHANGE_BITCOIN_DE,
  EXCHANGE_COINBASE,
  EXCHANGE_COINBASEPRO,
  EXCHANGE_GEMINI,
  EXCHANGE_ICONOMI,
  EXCHANGE_BITSTAMP
] as const;

export const SUPPORTED_TRADE_LOCATIONS = [
  EXCHANGE_UNISWAP,
  EXCHANGE_CRYPTOCOM,
  TRADE_LOCATION_EXTERNAL,
  TRADE_LOCATION_BANKS,
  TRADE_LOCATION_EQUITIES,
  TRADE_LOCATION_REALESTATE,
  TRADE_LOCATION_COMMODITIES,
  TRADE_LOCATION_BLOCKCHAIN
] as const;

export const ALL_TRADE_LOCATIONS = [
  ...SUPPORTED_TRADE_LOCATIONS,
  ...SUPPORTED_EXCHANGES
] as const;

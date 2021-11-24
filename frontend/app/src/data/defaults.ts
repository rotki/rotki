import { CurrencyLocation } from '@/types/currency-location';

export class Defaults {
  static DEFAULT_DATE_DISPLAY_FORMAT = '%d/%m/%Y %H:%M:%S %Z';
  static DEFAULT_THOUSAND_SEPARATOR = ',';
  static DEFAULT_DECIMAL_SEPARATOR = '.';
  static DEFAULT_CURRENCY_LOCATION = CurrencyLocation.AFTER;
  static FLOATING_PRECISION = 2;
  static RPC_ENDPOINT = 'http://localhost:8545';
  static KSM_RPC_ENDPOINT = 'http://localhost:9933';
  static DOT_RPC_ENDPOINT = ''; // same as Kusama, must be set by user
  static BALANCE_SAVE_FREQUENCY = 24;
  static ANONYMOUS_USAGE_ANALYTICS = true;
  static DEFAULT_QUERY_PERIOD = 5;
  static BTC_DERIVATION_GAP_LIMIT = 20;
  static DISPLAY_DATE_IN_LOCALTIME = true;
}

export const EXCHANGE_CRYPTOCOM = 'cryptocom';
export const EXCHANGE_BLOCKFI = 'blockfi';
export const EXCHANGE_NEXO = 'nexo';
export const EXCHANGE_SHAPESHIFT = 'shapeshift';
export const EXCHANGE_UPHOLD = 'uphold';

export const EXCHANGE_UNISWAP = 'uniswap';
export const EXCHANGE_BALANCER = 'balancer';
export const EXCHANGE_SUSHISWAP = 'sushiswap';

export const TRADE_LOCATION_EXTERNAL = 'external';
export const TRADE_LOCATION_BANKS = 'banks';
export const TRADE_LOCATION_EQUITIES = 'equities';
export const TRADE_LOCATION_REALESTATE = 'realestate';
export const TRADE_LOCATION_COMMODITIES = 'commodities';
export const TRADE_LOCATION_BLOCKCHAIN = 'blockchain';

export const SUPPORTED_TRADE_LOCATIONS = [
  EXCHANGE_UNISWAP,
  EXCHANGE_BALANCER,
  EXCHANGE_SUSHISWAP,
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_BLOCKFI,
  EXCHANGE_NEXO,
  EXCHANGE_SHAPESHIFT,
  EXCHANGE_UPHOLD,
  TRADE_LOCATION_EXTERNAL,
  TRADE_LOCATION_BANKS,
  TRADE_LOCATION_EQUITIES,
  TRADE_LOCATION_REALESTATE,
  TRADE_LOCATION_COMMODITIES,
  TRADE_LOCATION_BLOCKCHAIN
] as const;

export const EXTERNAL_EXCHANGES = [
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_BLOCKFI,
  EXCHANGE_NEXO,
  EXCHANGE_SHAPESHIFT,
  EXCHANGE_UPHOLD
];

import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import { TableColumn } from '@/types/table-column';

export class Defaults {
  static DEFAULT_DATE_DISPLAY_FORMAT =
    DateFormat.DateMonthYearHourMinuteSecondTimezone;
  static DEFAULT_DATE_INPUT_FORMAT = DateFormat.DateMonthYearHourMinuteSecond;
  static DEFAULT_VISIBLE_TIMEFRAMES = [
    TimeFramePeriod.ALL,
    TimeFramePeriod.YEAR,
    TimeFramePeriod.THREE_MONTHS,
    TimeFramePeriod.MONTH,
    TimeFramePeriod.TWO_WEEKS,
    TimeFramePeriod.WEEK
  ];
  static DEFAULT_THOUSAND_SEPARATOR = ',';
  static DEFAULT_DECIMAL_SEPARATOR = '.';
  static DEFAULT_CURRENCY_LOCATION = CurrencyLocation.AFTER;
  static FLOATING_PRECISION = 2;
  static KSM_RPC_ENDPOINT = 'http://localhost:9933';
  static DOT_RPC_ENDPOINT = ''; // same as Kusama, must be set by user
  static BALANCE_SAVE_FREQUENCY = 24;
  static ANONYMOUS_USAGE_ANALYTICS = true;
  static DEFAULT_QUERY_PERIOD = 5;
  static BTC_DERIVATION_GAP_LIMIT = 20;
  static DISPLAY_DATE_IN_LOCALTIME = true;
  static DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS = [
    TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE
  ];
  static DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY = 24;
}

export const EXCHANGE_BISQ = 'bisq';

export const EXCHANGE_BITMEX = 'bitmex';

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

export const TRADE_LOCATION_ETHEREUM = 'ethereum';

export const TRADE_LOCATION_OPTIMISM = 'optimism';

export const TRADE_LOCATION_POLYGON_POS = 'polygon_pos';

export const TRADE_LOCATION_ARBITRUM_ONE = 'arbitrum_one';

export const SUPPORTED_TRADE_LOCATIONS = [
  EXCHANGE_UNISWAP,
  EXCHANGE_BALANCER,
  EXCHANGE_SUSHISWAP,
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_BLOCKFI,
  EXCHANGE_NEXO,
  EXCHANGE_SHAPESHIFT,
  EXCHANGE_UPHOLD,
  EXCHANGE_BISQ,
  EXCHANGE_BITMEX,
  TRADE_LOCATION_EXTERNAL,
  TRADE_LOCATION_BANKS,
  TRADE_LOCATION_EQUITIES,
  TRADE_LOCATION_REALESTATE,
  TRADE_LOCATION_COMMODITIES,
  TRADE_LOCATION_BLOCKCHAIN,
  TRADE_LOCATION_ETHEREUM,
  TRADE_LOCATION_OPTIMISM,
  TRADE_LOCATION_POLYGON_POS
] as const;

export const EXTERNAL_EXCHANGES = [
  EXCHANGE_CRYPTOCOM,
  EXCHANGE_BLOCKFI,
  EXCHANGE_NEXO,
  EXCHANGE_SHAPESHIFT,
  EXCHANGE_UPHOLD,
  EXCHANGE_BISQ,
  EXCHANGE_BITMEX
];

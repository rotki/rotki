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
  static DEFAULT_QUERY_RETRY_LIMIT = 5;
  static DEFAULT_CONNECT_TIMEOUT = 30;
  static DEFAULT_READ_TIMEOUT = 30;
}

export const TRADE_LOCATION_EXTERNAL = 'external';

export const TRADE_LOCATION_BANKS = 'banks';

export const TRADE_LOCATION_BLOCKCHAIN = 'blockchain';

export const TRADE_LOCATION_ETHEREUM = 'ethereum';

export const TRADE_LOCATION_OPTIMISM = 'optimism';

export const TRADE_LOCATION_POLYGON_POS = 'polygon pos';

export const TRADE_LOCATION_ARBITRUM_ONE = 'arbitrum one';

export const TRADE_LOCATION_BASE = 'base';

export const TRADE_LOCATION_GNOSIS = 'gnosis';

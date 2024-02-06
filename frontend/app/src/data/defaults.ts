import { TimeFramePeriod } from '@rotki/common/lib/settings/graphs';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import { TableColumn } from '@/types/table-column';

export const Defaults = {
  DEFAULT_DATE_DISPLAY_FORMAT:
    DateFormat.DateMonthYearHourMinuteSecondTimezone,
  DEFAULT_DATE_INPUT_FORMAT: DateFormat.DateMonthYearHourMinuteSecond,
  DEFAULT_VISIBLE_TIMEFRAMES: [
    TimeFramePeriod.ALL,
    TimeFramePeriod.YEAR,
    TimeFramePeriod.THREE_MONTHS,
    TimeFramePeriod.MONTH,
    TimeFramePeriod.TWO_WEEKS,
    TimeFramePeriod.WEEK,
  ],
  DEFAULT_THOUSAND_SEPARATOR: ',',
  DEFAULT_DECIMAL_SEPARATOR: '.',
  DEFAULT_CURRENCY_LOCATION: CurrencyLocation.AFTER,
  FLOATING_PRECISION: 2,
  KSM_RPC_ENDPOINT: 'http://localhost:9933',
  DOT_RPC_ENDPOINT: '', // same as Kusama, must be set by user
  BEACON_RPC_ENDPOINT: '', // same as Kusama, must be set by user
  BALANCE_SAVE_FREQUENCY: 24,
  ANONYMOUS_USAGE_ANALYTICS: true,
  DEFAULT_QUERY_PERIOD: 5,
  BTC_DERIVATION_GAP_LIMIT: 20,
  DISPLAY_DATE_IN_LOCALTIME: true,
  DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS: [
    TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE,
  ],
  DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY: 24,
  DEFAULT_QUERY_RETRY_LIMIT: 5,
  DEFAULT_CONNECT_TIMEOUT: 30,
  DEFAULT_READ_TIMEOUT: 30,
  DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT: 5,
  DEFAULT_ORACLE_PENALTY_DURATION: 1800,
};

export const TRADE_LOCATION_EXTERNAL = 'external';

export const TRADE_LOCATION_BANKS = 'banks';

export const TRADE_LOCATION_BLOCKCHAIN = 'blockchain';

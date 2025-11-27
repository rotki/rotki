import { TimeFramePeriod } from '@rotki/common';
import { SECONDS_PER_DAY } from '@/data/constraints';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import { TableColumn } from '@/types/table-column';

export const Defaults = {
  ANONYMOUS_USAGE_ANALYTICS: true,
  BALANCE_SAVE_FREQUENCY: 24,
  BEACON_RPC_ENDPOINT: '', // same as Kusama, must be set by user
  BTC_DERIVATION_GAP_LIMIT: 20,
  DEFAULT_CONNECT_TIMEOUT: 30,
  DEFAULT_CSV_EXPORT_DELIMITER: ',',
  DEFAULT_CURRENCY_LOCATION: CurrencyLocation.AFTER,
  DEFAULT_DASHBOARD_TABLE_VISIBLE_COLUMNS: [TableColumn.PERCENTAGE_OF_TOTAL_NET_VALUE] satisfies TableColumn[],
  DEFAULT_DATE_DISPLAY_FORMAT: DateFormat.DateMonthYearHourMinuteSecondTimezone,
  DEFAULT_DATE_INPUT_FORMAT: DateFormat.DateMonthYearHourMinuteSecond,
  DEFAULT_DECIMAL_SEPARATOR: '.',
  DEFAULT_EVM_QUERY_INDICATOR_DISMISSAL_THRESHOLD: 6,
  DEFAULT_EVM_QUERY_INDICATOR_MIN_OUT_OF_SYNC_PERIOD: 12,
  DEFAULT_ORACLE_PENALTY_DURATION: 1800,
  DEFAULT_ORACLE_PENALTY_THRESHOLD_COUNT: 5,
  DEFAULT_PASSWORD_CONFIRMATION_INTERVAL: SECONDS_PER_DAY * 7,
  DEFAULT_QUERY_PERIOD: 5,
  DEFAULT_QUERY_RETRY_LIMIT: 5,
  DEFAULT_READ_TIMEOUT: 30,
  DEFAULT_THOUSAND_SEPARATOR: ',',
  DEFAULT_VERSION_UPDATE_CHECK_FREQUENCY: 24,
  DEFAULT_VISIBLE_TIMEFRAMES: [
    TimeFramePeriod.ALL,
    TimeFramePeriod.YEAR,
    TimeFramePeriod.THREE_MONTHS,
    TimeFramePeriod.MONTH,
    TimeFramePeriod.TWO_WEEKS,
    TimeFramePeriod.WEEK,
  ] satisfies TimeFramePeriod[],
  DISPLAY_DATE_IN_LOCALTIME: true,
  DOT_RPC_ENDPOINT: '', // same as Kusama, must be set by user
  FLOATING_PRECISION: 2,
  KSM_RPC_ENDPOINT: 'http://localhost:9933',
} as const;

export const TRADE_LOCATION_EXTERNAL = 'external';

export const TRADE_LOCATION_BANKS = 'banks';

export const TRADE_LOCATION_BLOCKCHAIN = 'blockchain';

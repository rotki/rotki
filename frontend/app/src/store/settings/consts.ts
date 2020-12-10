export const DEFI_SETUP_DONE = 'defiSetupDone' as 'defiSetupDone';
export const TIMEFRAME_SETTING = 'timeframeSetting' as 'timeframeSetting';
export const LAST_KNOWN_TIMEFRAME = 'lastKnownTimeframe' as 'lastKnownTimeframe';
export const QUERY_PERIOD = 'queryPeriod' as 'queryPeriod';

export const TIMEFRAME_ALL = 'All';
export const TIMEFRAME_YEAR = '1Y';
export const TIMEFRAME_THREE_MONTHS = '3M';
export const TIMEFRAME_MONTH = '1M';
export const TIMEFRAME_TWO_WEEKS = '2W';
export const TIMEFRAME_WEEK = '1W';
export const TIMEFRAME_REMEMBER = 'REMEMBER';

export const TIMEFRAME_PERIOD = [
  TIMEFRAME_ALL,
  TIMEFRAME_YEAR,
  TIMEFRAME_THREE_MONTHS,
  TIMEFRAME_MONTH,
  TIMEFRAME_TWO_WEEKS,
  TIMEFRAME_WEEK
] as const;

export const DEFI_SETUP_DONE = 'defiSetupDone' as 'defiSetupDone';
export const TIMEFRAME_SETTING = 'timeframeSetting' as 'timeframeSetting';
export const LAST_KNOWN_TIMEFRAME = 'lastKnownTimeframe' as 'lastKnownTimeframe';
export const QUERY_PERIOD = 'queryPeriod' as const;
export const PROFIT_LOSS_PERIOD = 'profitLossReportPeriod' as 'profitLossReportPeriod';
export const THOUSAND_SEPARATOR = 'thousandSeparator' as 'thousandSeparator';
export const DECIMAL_SEPARATOR = 'decimalSeparator' as 'decimalSeparator';
export const CURRENCY_LOCATION = 'currencyLocation' as 'currencyLocation';
export const REFRESH_PERIOD = 'refreshPeriod' as const;
export const EXPLORERS = 'explorers' as const;
export const ITEMS_PER_PAGE = 'itemsPerPage' as const;
export const AMOUNT_ROUNDING_MODE = 'amountRoundingMode' as const;
export const VALUE_ROUNDING_MODE = 'valueRoundingMode' as const;
export const DARK_MODE_ENABLED = 'darkModeEnabled' as const;
export const LIGHT_THEME = 'lightTheme' as const;
export const DARK_THEME = 'darkTheme' as const;

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

export const Q1 = 'Q1';
export const Q2 = 'Q2';
export const Q3 = 'Q3';
export const Q4 = 'Q4';
export const ALL = 'ALL';

export const QUARTERS = [Q1, Q2, Q3, Q4, ALL] as const;

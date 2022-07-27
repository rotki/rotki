import { SELECTED_THEME, Theme } from '@rotki/common/lib/settings';
import { TimeFrameSetting } from '@rotki/common/lib/settings/graphs';
import { SettingsState } from '@/store/settings/state';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import {
  DASHBOARD_TABLES_VISIBLE_COLUMNS,
  CURRENCY_LOCATION,
  DATE_INPUT_FORMAT,
  DECIMAL_SEPARATOR,
  VERSION_UPDATE_CHECK_FREQUENCY,
  PROFIT_LOSS_PERIOD,
  ProfitLossTimeframe,
  THOUSAND_SEPARATOR,
  DashboardTablesVisibleColumns,
  VISIBLE_TIMEFRAMES,
  LANGUAGE,
  SupportedLanguage
} from '@/types/frontend-settings';

type SettingsGetters = {
  [PROFIT_LOSS_PERIOD]: ProfitLossTimeframe;
  [LANGUAGE]: SupportedLanguage;
  [THOUSAND_SEPARATOR]: string;
  [DECIMAL_SEPARATOR]: string;
  [CURRENCY_LOCATION]: CurrencyLocation;
  [SELECTED_THEME]: Theme;
  [DASHBOARD_TABLES_VISIBLE_COLUMNS]: DashboardTablesVisibleColumns;
  [DATE_INPUT_FORMAT]: DateFormat;
  [VISIBLE_TIMEFRAMES]: TimeFrameSetting[];
  [VERSION_UPDATE_CHECK_FREQUENCY]: number;
};

export const getters: Getters<
  SettingsState,
  SettingsGetters,
  RotkehlchenState,
  any
> = {
  [PROFIT_LOSS_PERIOD]: state => state[PROFIT_LOSS_PERIOD],
  [LANGUAGE]: state => state[LANGUAGE],
  [THOUSAND_SEPARATOR]: state => state[THOUSAND_SEPARATOR],
  [DECIMAL_SEPARATOR]: state => state[DECIMAL_SEPARATOR],
  [CURRENCY_LOCATION]: state => state[CURRENCY_LOCATION],
  [SELECTED_THEME]: state => state[SELECTED_THEME],
  [DASHBOARD_TABLES_VISIBLE_COLUMNS]: state =>
    state[DASHBOARD_TABLES_VISIBLE_COLUMNS],
  [DATE_INPUT_FORMAT]: state => state[DATE_INPUT_FORMAT],
  [VISIBLE_TIMEFRAMES]: state => state[VISIBLE_TIMEFRAMES],
  [VERSION_UPDATE_CHECK_FREQUENCY]: state =>
    state[VERSION_UPDATE_CHECK_FREQUENCY]
};

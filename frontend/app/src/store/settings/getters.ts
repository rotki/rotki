import { DARK_MODE_ENABLED } from '@rotki/common/lib/settings';
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
  VISIBLE_TIMEFRAMES
} from '@/types/frontend-settings';

type SettingsGetters = {
  [PROFIT_LOSS_PERIOD]: ProfitLossTimeframe;
  [THOUSAND_SEPARATOR]: string;
  [DECIMAL_SEPARATOR]: string;
  [CURRENCY_LOCATION]: CurrencyLocation;
  [DARK_MODE_ENABLED]: boolean;
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
  [THOUSAND_SEPARATOR]: state => state[THOUSAND_SEPARATOR],
  [DECIMAL_SEPARATOR]: state => state[DECIMAL_SEPARATOR],
  [CURRENCY_LOCATION]: state => state[CURRENCY_LOCATION],
  [DARK_MODE_ENABLED]: state => state[DARK_MODE_ENABLED],
  [DASHBOARD_TABLES_VISIBLE_COLUMNS]: state =>
    state[DASHBOARD_TABLES_VISIBLE_COLUMNS],
  [DATE_INPUT_FORMAT]: state => state[DATE_INPUT_FORMAT],
  [VISIBLE_TIMEFRAMES]: state => state[VISIBLE_TIMEFRAMES],
  [VERSION_UPDATE_CHECK_FREQUENCY]: state =>
    state[VERSION_UPDATE_CHECK_FREQUENCY]
};

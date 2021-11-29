import { DARK_MODE_ENABLED } from '@rotki/common/lib/settings';
import { SettingsState } from '@/store/settings/state';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { CurrencyLocation } from '@/types/currency-location';
import {
  DASHBOARD_TABLES_VISIBLE_COLUMNS,
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  PROFIT_LOSS_PERIOD,
  ProfitLossTimeframe,
  THOUSAND_SEPARATOR,
  DashboardTablesVisibleColumns
} from '@/types/frontend-settings';

type SettingsGetters = {
  [PROFIT_LOSS_PERIOD]: ProfitLossTimeframe;
  [THOUSAND_SEPARATOR]: string;
  [DECIMAL_SEPARATOR]: string;
  [CURRENCY_LOCATION]: CurrencyLocation;
  [DARK_MODE_ENABLED]: boolean;
  [DASHBOARD_TABLES_VISIBLE_COLUMNS]: DashboardTablesVisibleColumns;
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
    state[DASHBOARD_TABLES_VISIBLE_COLUMNS]
};

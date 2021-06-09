import { default as BigNumber } from 'bignumber.js';
import { Defaults } from '@/data/defaults';
import { DARK_COLORS, LIGHT_COLORS } from '@/plugins/theme';
import {
  ALL,
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD,
  PROFIT_LOSS_PERIOD,
  THOUSAND_SEPARATOR,
  TIMEFRAME_ALL,
  TIMEFRAME_REMEMBER,
  TIMEFRAME_SETTING,
  REFRESH_PERIOD,
  EXPLORERS,
  ITEMS_PER_PAGE,
  AMOUNT_ROUNDING_MODE,
  VALUE_ROUNDING_MODE,
  DARK_MODE_ENABLED,
  DARK_THEME,
  LIGHT_THEME,
  GRAPH_ZERO_BASED
} from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';

export const defaultState: () => SettingsState = () => ({
  [DEFI_SETUP_DONE]: false,
  [TIMEFRAME_SETTING]: TIMEFRAME_REMEMBER,
  [LAST_KNOWN_TIMEFRAME]: TIMEFRAME_ALL,
  [QUERY_PERIOD]: Defaults.DEFAULT_QUERY_PERIOD,
  [PROFIT_LOSS_PERIOD]: {
    year: new Date().getFullYear().toString(),
    quarter: ALL
  },
  [THOUSAND_SEPARATOR]: Defaults.DEFAULT_THOUSAND_SEPARATOR,
  [DECIMAL_SEPARATOR]: Defaults.DEFAULT_DECIMAL_SEPARATOR,
  [CURRENCY_LOCATION]: Defaults.DEFAULT_CURRENCY_LOCATION,
  [REFRESH_PERIOD]: -1,
  [EXPLORERS]: {},
  [ITEMS_PER_PAGE]: 10,
  [AMOUNT_ROUNDING_MODE]: BigNumber.ROUND_UP,
  [VALUE_ROUNDING_MODE]: BigNumber.ROUND_DOWN,
  [DARK_MODE_ENABLED]: false,
  [LIGHT_THEME]: LIGHT_COLORS,
  [DARK_THEME]: DARK_COLORS,
  [GRAPH_ZERO_BASED]: false
});

export const state: SettingsState = defaultState();

import { Defaults } from '@/data/defaults';
import {
  ALL,
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD,
  TAX_REPORT_PERIOD,
  THOUSAND_SEPARATOR,
  TIMEFRAME_ALL,
  TIMEFRAME_REMEMBER,
  TIMEFRAME_SETTING
} from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';

export const defaultState: () => SettingsState = () => ({
  [DEFI_SETUP_DONE]: false,
  [TIMEFRAME_SETTING]: TIMEFRAME_REMEMBER,
  [LAST_KNOWN_TIMEFRAME]: TIMEFRAME_ALL,
  [QUERY_PERIOD]: Defaults.DEFAULT_QUERY_PERIOD,
  [TAX_REPORT_PERIOD]: {
    year: new Date().getFullYear().toString(),
    quarter: ALL
  },
  [THOUSAND_SEPARATOR]: Defaults.DEFAULT_THOUSAND_SEPARATOR,
  [DECIMAL_SEPARATOR]: Defaults.DEFAULT_DECIMAL_SEPARATOR,
  [CURRENCY_LOCATION]: Defaults.DEFAULT_CURRENCY_LOCATION
});

export const state: SettingsState = defaultState();

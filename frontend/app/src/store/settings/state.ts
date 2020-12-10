import { Defaults } from '@/data/defaults';
import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  TIMEFRAME_ALL,
  TIMEFRAME_REMEMBER,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD
} from '@/store/settings/consts';
import { SettingsState } from '@/store/settings/types';

export const defaultState: () => SettingsState = () => ({
  [DEFI_SETUP_DONE]: false,
  [TIMEFRAME_SETTING]: TIMEFRAME_REMEMBER,
  [LAST_KNOWN_TIMEFRAME]: TIMEFRAME_ALL,
  [QUERY_PERIOD]: Defaults.DEFAULT_QUERY_PERIOD
});

export const state: SettingsState = defaultState();

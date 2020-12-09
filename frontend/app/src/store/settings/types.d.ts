import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  TIMEFRAME_PERIOD,
  TIMEFRAME_REMEMBER,
  LAST_KNOWN_TIMEFRAME
} from '@/store/settings/consts';

export type TimeFramePeriod = typeof TIMEFRAME_PERIOD[number];
export type TimeFrameSetting = TimeFramePeriod | typeof TIMEFRAME_REMEMBER;

export interface SettingsState {
  readonly [DEFI_SETUP_DONE]: boolean;
  readonly [TIMEFRAME_SETTING]: TimeFrameSetting;
  readonly [LAST_KNOWN_TIMEFRAME]: TimeFramePeriod;
}

export type FrontendSettingsPayload = {
  +readonly [P in keyof SettingsState]+?: SettingsState[P];
};

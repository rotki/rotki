import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  TIMEFRAME_PERIOD,
  TIMEFRAME_REMEMBER,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD,
  TAX_REPORT_PERIOD,
  QUARTERS
} from '@/store/settings/consts';

export type TimeFramePeriod = typeof TIMEFRAME_PERIOD[number];
export type TimeFrameSetting = TimeFramePeriod | typeof TIMEFRAME_REMEMBER;

export type Quarter = typeof QUARTERS[number];

export type TaxReportPeriod = {
  readonly year: string;
  readonly quarter: Quarter;
};

export interface SettingsState {
  readonly [DEFI_SETUP_DONE]: boolean;
  readonly [TIMEFRAME_SETTING]: TimeFrameSetting;
  readonly [LAST_KNOWN_TIMEFRAME]: TimeFramePeriod;
  readonly [QUERY_PERIOD]: number;
  readonly [TAX_REPORT_PERIOD]: TaxReportPeriod;
}

export type FrontendSettingsPayload = {
  +readonly [P in keyof SettingsState]+?: SettingsState[P];
};

import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  TIMEFRAME_PERIOD,
  TIMEFRAME_REMEMBER,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD,
  PROFIT_LOSS_PERIOD,
  QUARTERS,
  THOUSAND_SEPARATOR,
  DECIMAL_SEPARATOR,
  CURRENCY_LOCATION
} from '@/store/settings/consts';
import { CurrencyLocation } from '@/typing/types';

export type TimeFramePeriod = typeof TIMEFRAME_PERIOD[number];
export type TimeFrameSetting = TimeFramePeriod | typeof TIMEFRAME_REMEMBER;

export type Quarter = typeof QUARTERS[number];

export type ProfitLossTimeframe = {
  readonly year: string;
  readonly quarter: Quarter;
};

export interface SettingsState {
  readonly [DEFI_SETUP_DONE]: boolean;
  readonly [TIMEFRAME_SETTING]: TimeFrameSetting;
  readonly [LAST_KNOWN_TIMEFRAME]: TimeFramePeriod;
  readonly [QUERY_PERIOD]: number;
  readonly [PROFIT_LOSS_PERIOD]: ProfitLossTimeframe;
  readonly [THOUSAND_SEPARATOR]: string;
  readonly [DECIMAL_SEPARATOR]: string;
  readonly [CURRENCY_LOCATION]: CurrencyLocation;
}

export type FrontendSettingsPayload = {
  +readonly [P in keyof SettingsState]+?: SettingsState[P];
};

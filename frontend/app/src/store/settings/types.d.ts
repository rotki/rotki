import { default as BigNumber } from 'bignumber.js';
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
  CURRENCY_LOCATION,
  REFRESH_PERIOD,
  EXPLORERS,
  ITEMS_PER_PAGE,
  AMOUNT_ROUNDING_MODE,
  VALUE_ROUNDING_MODE,
  DARK_MODE_ENABLED,
  LIGHT_THEME,
  DARK_THEME,
  GRAPH_ZERO_BASED
} from '@/store/settings/consts';
import { CurrencyLocation } from '@/typing/types';
import RoundingMode = BigNumber.RoundingMode;

export type TimeFramePeriod = typeof TIMEFRAME_PERIOD[number];
export type TimeFrameSetting = TimeFramePeriod | typeof TIMEFRAME_REMEMBER;

export type Quarter = typeof QUARTERS[number];

export type ProfitLossTimeframe = {
  readonly year: string;
  readonly quarter: Quarter;
};

export type RefreshPeriod = number;

export type ExplorerEndpoints = {
  readonly transaction?: string;
  readonly address?: string;
};

export type ExplorersSettings = {
  readonly ETC?: ExplorerEndpoints;
  readonly ETH?: ExplorerEndpoints;
  readonly BTC?: ExplorerEndpoints;
  readonly KSM?: ExplorerEndpoints;
  readonly AVAX?: ExplorerEndpoints;
};

export interface Themes {
  readonly light: ThemeColors;
  readonly dark: ThemeColors;
}

export type ThemeColors = {
  readonly primary: string;
  readonly accent: string;
  readonly graph: string;
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
  readonly [REFRESH_PERIOD]: RefreshPeriod;
  readonly [EXPLORERS]: ExplorersSettings;
  readonly [ITEMS_PER_PAGE]: number;
  readonly [AMOUNT_ROUNDING_MODE]: RoundingMode;
  readonly [VALUE_ROUNDING_MODE]: RoundingMode;
  readonly [DARK_MODE_ENABLED]: boolean;
  readonly [LIGHT_THEME]: ThemeColors;
  readonly [DARK_THEME]: ThemeColors;
  readonly [GRAPH_ZERO_BASED]: boolean;
}

export type FrontendSettingsPayload = Partial<SettingsState>;

import {
  DARK_MODE_ENABLED,
  DARK_THEME,
  LIGHT_THEME,
  ThemeColors
} from '@rotki/common/lib/settings';
import {
  TimeFramePeriod,
  TimeFrameSetting
} from '@rotki/common/lib/settings/graphs';
import { defaultState, SettingsState } from '@/store/settings/state';
import { Writeable } from '@/types';
import { CurrencyLocation } from '@/types/currency-location';
import { DateFormat } from '@/types/date-format';
import {
  AMOUNT_ROUNDING_MODE,
  CURRENCY_LOCATION,
  DECIMAL_SEPARATOR,
  DEFI_SETUP_DONE,
  EXPLORERS,
  ExplorersSettings,
  GRAPH_ZERO_BASED,
  ITEMS_PER_PAGE,
  LAST_KNOWN_TIMEFRAME,
  PROFIT_LOSS_PERIOD,
  ProfitLossTimeframe,
  QUERY_PERIOD,
  REFRESH_PERIOD,
  RefreshPeriod,
  RoundingMode,
  THOUSAND_SEPARATOR,
  TIMEFRAME_SETTING,
  VALUE_ROUNDING_MODE,
  NFTS_IN_NET_VALUE,
  DASHBOARD_TABLES_VISIBLE_COLUMNS,
  DashboardTablesVisibleColumns,
  DATE_INPUT_FORMAT,
  VISIBLE_TIMEFRAMES,
  VERSION_UPDATE_CHECK_FREQUENCY
} from '@/types/frontend-settings';

type Mutations<S = SettingsState> = {
  [DEFI_SETUP_DONE](state: S, done: boolean): void;
  [TIMEFRAME_SETTING](state: S, timeframe: TimeFrameSetting): void;
  [VISIBLE_TIMEFRAMES](state: S, timeframes: TimeFrameSetting[]): void;
  [LAST_KNOWN_TIMEFRAME](state: S, timeframe: TimeFramePeriod): void;
  [QUERY_PERIOD](state: S, period: number): void;
  [PROFIT_LOSS_PERIOD](state: S, period: ProfitLossTimeframe): void;
  [THOUSAND_SEPARATOR](state: S, separator: string): void;
  [DECIMAL_SEPARATOR](state: S, separator: string): void;
  [CURRENCY_LOCATION](state: S, location: CurrencyLocation): void;
  [REFRESH_PERIOD](state: S, period: RefreshPeriod): void;
  [EXPLORERS](state: S, explorers: ExplorersSettings): void;
  [ITEMS_PER_PAGE](state: S, itemsPerPage: number): void;
  [AMOUNT_ROUNDING_MODE](state: S, mode: RoundingMode): void;
  [VALUE_ROUNDING_MODE](state: S, mode: RoundingMode): void;
  [DARK_MODE_ENABLED](state: S, enabled: boolean): void;
  [LIGHT_THEME](state: S, theme: ThemeColors): void;
  [DARK_THEME](state: S, theme: ThemeColors): void;
  [GRAPH_ZERO_BASED](state: S, enabled: Boolean): void;
  [NFTS_IN_NET_VALUE](state: S, enabled: Boolean): void;
  [DASHBOARD_TABLES_VISIBLE_COLUMNS](
    state: Writeable<SettingsState>,
    tablesVisibleColumns: DashboardTablesVisibleColumns
  ): void;
  [DATE_INPUT_FORMAT](state: S, format: DateFormat): void;
  [VERSION_UPDATE_CHECK_FREQUENCY](state: S, period: number): void;
  restore(state: S, persisted: S): void;
  reset(state: S): void;
};

export const mutations: Mutations = {
  [DEFI_SETUP_DONE](state: Writeable<SettingsState>, done: boolean) {
    state[DEFI_SETUP_DONE] = done;
  },
  [TIMEFRAME_SETTING](
    state: Writeable<SettingsState>,
    timeframe: TimeFrameSetting
  ) {
    state[TIMEFRAME_SETTING] = timeframe;
  },
  [VISIBLE_TIMEFRAMES](
    state: Writeable<SettingsState>,
    timeframes: TimeFrameSetting[]
  ) {
    state[VISIBLE_TIMEFRAMES] = timeframes;
  },
  [LAST_KNOWN_TIMEFRAME](
    state: Writeable<SettingsState>,
    timeframe: TimeFramePeriod
  ) {
    state[LAST_KNOWN_TIMEFRAME] = timeframe;
  },
  [QUERY_PERIOD](state: Writeable<SettingsState>, period: number) {
    state[QUERY_PERIOD] = period;
  },
  [PROFIT_LOSS_PERIOD](
    state: Writeable<SettingsState>,
    period: ProfitLossTimeframe
  ) {
    state[PROFIT_LOSS_PERIOD] = period;
  },
  [THOUSAND_SEPARATOR](state: Writeable<SettingsState>, separator: string) {
    state[THOUSAND_SEPARATOR] = separator;
  },
  [DECIMAL_SEPARATOR](state: Writeable<SettingsState>, separator: string) {
    state[DECIMAL_SEPARATOR] = separator;
  },
  [CURRENCY_LOCATION](
    state: Writeable<SettingsState>,
    location: CurrencyLocation
  ) {
    state[CURRENCY_LOCATION] = location;
  },
  [REFRESH_PERIOD](state: Writeable<SettingsState>, period: RefreshPeriod) {
    state.refreshPeriod = period;
  },
  [EXPLORERS](state: Writeable<SettingsState>, explorers: ExplorersSettings) {
    state.explorers = explorers;
  },
  [ITEMS_PER_PAGE](state: Writeable<SettingsState>, itemsPerPage: number) {
    state.itemsPerPage = itemsPerPage;
  },
  [AMOUNT_ROUNDING_MODE](
    state: Writeable<SettingsState>,
    roundingMode: RoundingMode
  ) {
    state.amountRoundingMode = roundingMode;
  },
  [VALUE_ROUNDING_MODE](
    state: Writeable<SettingsState>,
    roundingMode: RoundingMode
  ) {
    state.valueRoundingMode = roundingMode;
  },
  [DARK_MODE_ENABLED](state: Writeable<SettingsState>, enabled: boolean) {
    state.darkModeEnabled = enabled;
  },
  [LIGHT_THEME](state: Writeable<SettingsState>, theme: ThemeColors) {
    state[LIGHT_THEME] = theme;
  },
  [DARK_THEME](state: Writeable<SettingsState>, theme: ThemeColors) {
    state[DARK_THEME] = theme;
  },
  [GRAPH_ZERO_BASED](state: Writeable<SettingsState>, enabled: boolean) {
    state[GRAPH_ZERO_BASED] = enabled;
  },
  [NFTS_IN_NET_VALUE](state: Writeable<SettingsState>, enabled: boolean) {
    state[NFTS_IN_NET_VALUE] = enabled;
  },
  [DASHBOARD_TABLES_VISIBLE_COLUMNS](
    state: Writeable<SettingsState>,
    tablesVisibleColumns: DashboardTablesVisibleColumns
  ) {
    state[DASHBOARD_TABLES_VISIBLE_COLUMNS] = tablesVisibleColumns;
  },
  [DATE_INPUT_FORMAT](state: Writeable<SettingsState>, format: DateFormat) {
    state[DATE_INPUT_FORMAT] = format;
  },
  [VERSION_UPDATE_CHECK_FREQUENCY](
    state: Writeable<SettingsState>,
    period: number
  ) {
    state[VERSION_UPDATE_CHECK_FREQUENCY] = period;
  },
  restore(state: SettingsState, persisted: SettingsState) {
    Object.assign(state, persisted);
  },
  reset: (state: SettingsState) => {
    Object.assign(state, defaultState());
  }
};

import { default as BigNumber } from 'bignumber.js';
import {
  TIMEFRAME_SETTING,
  DEFI_SETUP_DONE,
  LAST_KNOWN_TIMEFRAME,
  QUERY_PERIOD,
  PROFIT_LOSS_PERIOD,
  THOUSAND_SEPARATOR,
  DECIMAL_SEPARATOR,
  CURRENCY_LOCATION,
  REFRESH_PERIOD,
  EXPLORERS,
  ITEMS_PER_PAGE,
  AMOUNT_ROUNDING_MODE,
  VALUE_ROUNDING_MODE
} from '@/store/settings/consts';
import { defaultState } from '@/store/settings/state';
import {
  SettingsState,
  ProfitLossTimeframe,
  TimeFramePeriod,
  TimeFrameSetting,
  RefreshPeriod,
  ExplorersSettings
} from '@/store/settings/types';
import { Writeable } from '@/types';
import { CurrencyLocation } from '@/typing/types';
import RoundingMode = BigNumber.RoundingMode;

type Mutations<S = SettingsState> = {
  [DEFI_SETUP_DONE](state: S, done: boolean): void;
  [TIMEFRAME_SETTING](state: S, timeframe: TimeFrameSetting): void;
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
  restore(state: SettingsState, persisted: SettingsState) {
    Object.assign(state, persisted);
  },
  reset: (state: SettingsState) => {
    Object.assign(state, defaultState());
  }
};

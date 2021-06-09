import { Currency } from '@/model/currency';
import {
  SupportedModules,
  Watcher,
  WatcherType
} from '@/services/session/types';
import { SessionState } from '@/store/session/types';
import { RotkehlchenState } from '@/store/types';
import { Getters } from '@/store/typing';
import { Tag } from '@/typing/types';

interface SessionGetters {
  floatingPrecision: number;
  dateDisplayFormat: string;
  currency: Currency;
  tags: Tag[];
  loanWatchers: Watcher<WatcherType>[];
  activeModules: SupportedModules[];
  currencySymbol: string;
}

export const getters: Getters<
  SessionState,
  SessionGetters,
  RotkehlchenState,
  any
> = {
  floatingPrecision: (state: SessionState) => {
    return state.generalSettings.floatingPrecision;
  },

  dateDisplayFormat: (state: SessionState) => {
    return state.generalSettings.dateDisplayFormat;
  },

  currency: (state: SessionState) => {
    return state.generalSettings.selectedCurrency;
  },

  currencySymbol: (_, getters) => {
    return getters.currency.ticker_symbol;
  },

  tags: (state: SessionState) => {
    return Object.values(state.tags);
  },

  loanWatchers: ({ watchers }) => {
    const loanWatcherTypes = ['makervault_collateralization_ratio'];

    return watchers.filter(
      watcher => loanWatcherTypes.indexOf(watcher.type) > -1
    );
  },

  activeModules: ({ generalSettings }) => {
    return generalSettings.activeModules;
  }
};
